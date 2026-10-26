import logging
import time
from email.utils import formataddr

from sqlalchemy import select

from . import db
from .backends import FatalSendError, RetryableError, SendError
from .models import Campaign, Contact, Message, Setting, list_members, utcnow
from .rendering import render_email

log = logging.getLogger("mailer")

MAX_RETRIES = 5


def sender_address():
    from_email = Setting.get("from_email")
    if not from_email:
        raise FatalSendError("No 'From' email address set. Add one on the Settings page.")
    return formataddr((Setting.get("from_name"), from_email))


def recipients_query(campaign):
    """Subscribed contacts on any of the campaign's lists, each counted once."""
    list_ids = [l.id for l in campaign.lists]
    member_ids = select(list_members.c.contact_id).where(list_members.c.list_id.in_(list_ids))
    return Contact.query.filter(Contact.status == "subscribed", Contact.id.in_(member_ids))


def start_campaign(campaign):
    """Freeze the recipient list into queued Message rows and mark the campaign as sending."""
    existing = {cid for (cid,) in db.session.query(Message.contact_id).filter_by(campaign_id=campaign.id)}
    for contact in recipients_query(campaign):
        if contact.id not in existing:
            db.session.add(Message(campaign_id=campaign.id, contact_id=contact.id, email=contact.email))
    campaign.status = "sending"
    campaign.started_at = campaign.started_at or utcnow()
    campaign.last_error = None
    db.session.commit()


def start_due_campaigns():
    due = Campaign.query.filter(Campaign.status == "scheduled", Campaign.scheduled_at <= utcnow()).all()
    for campaign in due:
        log.info("Starting scheduled campaign %s", campaign.name)
        start_campaign(campaign)


def send_one(backend, campaign, message, from_addr, reply_to):
    contact = message.contact
    if contact is None or contact.status != "subscribed":
        message.status = "skipped"
        message.error = "Unsubscribed or removed before sending"
        return
    subject, html, text = render_email(campaign, contact)
    for attempt in range(MAX_RETRIES):
        try:
            message.ses_message_id = backend.send(
                from_addr=from_addr,
                to=message.email,
                subject=subject,
                html=html,
                text=text,
                reply_to=reply_to,
                tags={"campaign": campaign.id, "message": message.id},
            )
            message.status = "sent"
            message.sent_at = utcnow()
            return
        except RetryableError as exc:
            wait = 2 ** attempt
            log.warning("SES throttled (%s); retrying in %ss", exc, wait)
            time.sleep(wait)
        except SendError as exc:
            message.status = "failed"
            message.error = str(exc)
            return
    message.status = "failed"
    message.error = "Gave up after repeated throttling"


def send_campaign(backend, campaign_id, should_stop=lambda: False):
    """Send every queued message for a campaign. Safe to call again after a crash."""
    campaign = db.session.get(Campaign, campaign_id)
    try:
        from_addr = sender_address()
    except FatalSendError as exc:
        _pause(campaign, str(exc))
        return

    reply_to = Setting.get("reply_to") or None
    interval = 1.0 / max(backend.max_send_rate() * 0.9, 0.1)  # stay just under the SES limit

    while not should_stop():
        db.session.refresh(campaign)
        if campaign.status != "sending":
            return  # cancelled or paused from the dashboard
        batch = (
            Message.query.filter_by(campaign_id=campaign.id, status="queued")
            .order_by(Message.id)
            .limit(50)
            .all()
        )
        if not batch:
            campaign.status = "sent"
            campaign.finished_at = utcnow()
            db.session.commit()
            log.info("Campaign %s finished", campaign.name)
            return
        for message in batch:
            if should_stop():
                return
            started = time.monotonic()
            try:
                send_one(backend, campaign, message, from_addr, reply_to)
            except FatalSendError as exc:
                db.session.rollback()
                _pause(campaign, str(exc))
                return
            db.session.commit()  # commit per email so a restart never double-sends
            elapsed = time.monotonic() - started
            if elapsed < interval:
                time.sleep(interval - elapsed)


def _pause(campaign, reason):
    log.error("Pausing campaign %s: %s", campaign.name, reason)
    campaign.status = "paused"
    campaign.last_error = reason
    db.session.commit()
