import logging
from datetime import datetime

from . import db
from .models import Contact, Event, Message, utcnow

log = logging.getLogger("mailer")


def _parse_ts(value):
    if not value:
        return utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return utcnow()


def _unsubscribed(subscription):
    prefs = subscription.get("newTopicPreferences") or {}
    if prefs.get("unsubscribeAll"):
        return True
    return any(
        (t.get("subscriptionStatus") or "").upper().replace("_", "") == "OPTOUT"
        for t in prefs.get("topicSubscriptionStatus") or []
    )


def apply_event(event):
    """Record one SES event. Returns True if it matched a message we sent."""
    event_type = event.get("eventType") or event.get("notificationType")
    mail = event.get("mail") or {}
    ses_id = mail.get("messageId")
    message = Message.query.filter_by(ses_message_id=ses_id).first() if ses_id else None
    if message is None:
        # The event can beat the sender's database commit; fall back to our own tag.
        tag = (mail.get("tags") or {}).get("message") or [None]
        if str(tag[0] or "").isdigit():
            message = db.session.get(Message, int(tag[0]))
    if message is None:
        log.debug("Ignoring %s event for unknown message %s", event_type, ses_id)
        return False

    detail = None
    contact = message.contact

    if event_type == "Delivery":
        ts = _parse_ts(event.get("delivery", {}).get("timestamp"))
        message.delivered_at = message.delivered_at or ts
    elif event_type == "Open":
        ts = _parse_ts(event.get("open", {}).get("timestamp"))
        message.opened_at = message.opened_at or ts
        message.open_count = (message.open_count or 0) + 1
    elif event_type == "Click":
        click = event.get("click", {})
        ts = _parse_ts(click.get("timestamp"))
        detail = click.get("link")
        message.clicked_at = message.clicked_at or ts
        message.click_count = (message.click_count or 0) + 1
        # A click proves the email was opened even if images were blocked.
        message.opened_at = message.opened_at or ts
    elif event_type == "Bounce":
        bounce = event.get("bounce", {})
        ts = _parse_ts(bounce.get("timestamp"))
        bounce_type = bounce.get("bounceType", "Undetermined")
        message.bounced_at = message.bounced_at or ts
        message.bounce_type = bounce_type
        detail = bounce_type
        # Soft ("Transient") bounces are temporary; only stop emailing hard bounces.
        if bounce_type == "Permanent" and contact:
            contact.suppress("bounced")
    elif event_type == "Complaint":
        ts = _parse_ts(event.get("complaint", {}).get("timestamp"))
        message.complained_at = message.complained_at or ts
        if contact:
            contact.suppress("complained")
    elif event_type == "Subscription":
        subscription = event.get("subscription", {})
        ts = _parse_ts(subscription.get("timestamp"))
        if not _unsubscribed(subscription):
            return True
        message.unsubscribed_at = message.unsubscribed_at or ts
        if contact:
            contact.suppress("unsubscribed")
    elif event_type in ("Send", "Reject", "RenderingFailure", "DeliveryDelay"):
        ts = _parse_ts((event.get("mail") or {}).get("timestamp"))
        if event_type in ("Reject", "RenderingFailure"):
            message.status = "failed"
            message.error = event_type
    else:
        return True

    db.session.add(
        Event(message_id=message.id, campaign_id=message.campaign_id, type=event_type, timestamp=ts, detail=detail)
    )
    return True


def poll_events(backend, wait_seconds=10):
    """Pull pending events from AWS and apply them. Returns how many were processed."""
    processed = 0
    for event, ack in backend.receive_events(wait_seconds=wait_seconds):
        try:
            apply_event(event)
            db.session.commit()
        except Exception:  # noqa: BLE001 - keep the queue moving; the bad event stays for a retry
            db.session.rollback()
            log.exception("Could not process event %s", event.get("eventType"))
            continue
        ack()
        processed += 1
    return processed


def sync_unsubscribes(backend):
    """Safety net: copy any opt-outs held in the SES contact list into our database."""
    emails = set(backend.unsubscribed_emails())
    if not emails:
        return 0
    changed = 0
    for contact in Contact.query.filter(Contact.status == "subscribed", Contact.email.in_(emails)):
        contact.suppress("unsubscribed")
        changed += 1
    db.session.commit()
    return changed
