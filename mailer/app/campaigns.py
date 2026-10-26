import re
from datetime import datetime, timezone
from types import SimpleNamespace

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .analytics import campaign_stats, campaign_timeline, top_links
from .backends import FatalSendError, SendError, get_backend
from .models import Campaign, ContactList, Event, Message, Setting, utcnow
from .permissions import editor_required
from .rendering import SAMPLE_CONTACT, normalise_tags, render_email, validate_template
from .sender import recipients_query, sender_address

bp = Blueprint("campaigns", __name__, url_prefix="/campaigns")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STARTER_BODY = (
    "<p>Hi {{ first_name }},</p>\n<p>Write your message here.</p>\n<p>Thanks,<br>The team</p>"
)


@bp.route("/")
@login_required
def index():
    campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template(
        "campaigns/index.html", campaigns=campaigns, stats=campaign_stats([c.id for c in campaigns])
    )


@bp.route("/new", methods=["GET", "POST"])
@editor_required
def new():
    campaign = Campaign(name="", subject="", body_html=STARTER_BODY)
    return _edit_form(campaign, is_new=True)


@bp.route("/<int:campaign_id>/edit", methods=["GET", "POST"])
@editor_required
def edit(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    if not campaign.editable:
        flash("This campaign has already been sent and can't be edited. Duplicate it instead.", "error")
        return redirect(url_for("campaigns.report", campaign_id=campaign.id))
    return _edit_form(campaign)


def _edit_form(campaign, is_new=False):
    lists = ContactList.query.order_by(ContactList.name).all()
    if request.method == "POST":
        fields = {
            "name": request.form.get("name", "").strip(),
            "subject": request.form.get("subject", "").strip(),
            "preview_text": request.form.get("preview_text", "").strip(),
            "body_html": normalise_tags(request.form.get("body_html", "")),
        }
        selected = {int(i) for i in request.form.getlist("list_ids") if i.isdigit()}

        problems = []
        if not fields["name"]:
            problems.append("Give the campaign a name.")
        if not fields["subject"]:
            problems.append("Add a subject line.")
        for key in ("subject", "preview_text", "body_html"):
            problem = validate_template(fields[key])
            if problem:
                problems.append(problem)
        if problems:
            # Leave the saved campaign untouched; re-show the form with what the user typed.
            for p in problems:
                flash(p, "error")
            shown = SimpleNamespace(id=campaign.id, status=campaign.status,
                                    scheduled_at=campaign.scheduled_at, **fields)
            return render_template("campaigns/edit.html", campaign=shown, lists=lists, is_new=is_new,
                                   selected=selected)
        for key, value in fields.items():
            setattr(campaign, key, value)
        campaign.lists = [l for l in lists if l.id in selected]
        if is_new:
            campaign.created_by_id = current_user.id
            db.session.add(campaign)
        db.session.commit()
        flash("Campaign saved.", "success")
        if request.form.get("next") == "send":
            return redirect(url_for("campaigns.send", campaign_id=campaign.id))
        return redirect(url_for("campaigns.edit", campaign_id=campaign.id))
    return render_template("campaigns/edit.html", campaign=campaign, lists=lists, is_new=is_new,
                           selected={l.id for l in campaign.lists})


@bp.route("/<int:campaign_id>/preview")
@login_required
def preview(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    sample = recipients_query(campaign).first() if campaign.lists else None
    _, html, _ = render_email(campaign, sample or SAMPLE_CONTACT, unsubscribe_url="#unsubscribe")
    return html


@bp.route("/<int:campaign_id>/test", methods=["POST"])
@editor_required
def test_send(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    addresses = [a.strip() for a in re.split(r"[,;\s]+", request.form.get("emails", "")) if a.strip()]
    if not addresses or len(addresses) > 5 or not all(EMAIL_RE.match(a) for a in addresses):
        flash("Enter up to 5 valid email addresses, separated by commas.", "error")
        return redirect(request.referrer or url_for("campaigns.edit", campaign_id=campaign.id))
    backend = get_backend(current_app.config)
    sample = recipients_query(campaign).first() if campaign.lists else None
    try:
        subject, html, text = render_email(campaign, sample or SAMPLE_CONTACT)
        for address in addresses:
            backend.send(
                from_addr=sender_address(),
                to=address,
                subject=f"[TEST] {subject}",
                html=html,
                text=text,
                reply_to=Setting.get("reply_to") or None,
            )
    except (SendError, FatalSendError) as exc:
        flash(f"Test send failed: {exc}", "error")
    else:
        note = " (demo mode: logged, not really sent)" if backend.name == "console" else ""
        flash(f"Test sent to {', '.join(addresses)}{note}.", "success")
    return redirect(request.referrer or url_for("campaigns.edit", campaign_id=campaign.id))


@bp.route("/<int:campaign_id>/send", methods=["GET", "POST"])
@editor_required
def send(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    if not campaign.editable:
        return redirect(url_for("campaigns.report", campaign_id=campaign.id))
    recipient_count = recipients_query(campaign).count() if campaign.lists else 0

    if request.method == "POST":
        problems = []
        if not campaign.lists or not recipient_count:
            problems.append("This campaign has no subscribed recipients. Pick a list on the edit page.")
        if not Setting.get("from_email"):
            problems.append("Set a 'From' address on the Settings page first.")
        if not Setting.get("postal_address"):
            problems.append("Add your postal address on the Settings page (required by law in marketing emails).")
        if request.form.get("confirm") != "yes":
            problems.append("Tick the box to confirm.")

        when = utcnow()
        if request.form.get("mode") == "schedule":
            try:
                # The browser sends the host computer's local time; store it as UTC.
                local = datetime.fromisoformat(request.form.get("scheduled_at", ""))
                when = local.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                problems.append("Pick a valid date and time.")
            else:
                if when <= utcnow():
                    problems.append("The scheduled time is in the past.")
        if problems:
            for p in problems:
                flash(p, "error")
            return redirect(url_for("campaigns.send", campaign_id=campaign.id))

        campaign.status = "scheduled"
        campaign.scheduled_at = when
        db.session.commit()
        if request.form.get("mode") == "schedule":
            flash("Campaign scheduled.", "success")
        else:
            flash("Sending has started. This page updates live.", "success")
        return redirect(url_for("campaigns.report", campaign_id=campaign.id))

    backend = get_backend(current_app.config)
    try:
        account = backend.account_status()
    except Exception as exc:  # noqa: BLE001
        account = {"error": str(exc)}
    return render_template(
        "campaigns/send.html", campaign=campaign, recipient_count=recipient_count, account=account
    )


@bp.route("/<int:campaign_id>/action", methods=["POST"])
@editor_required
def action(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    act = request.form.get("action")
    if act == "unschedule" and campaign.status == "scheduled":
        campaign.status = "draft"
        campaign.scheduled_at = None
        flash("Campaign moved back to draft.", "success")
    elif act == "pause" and campaign.status == "sending":
        campaign.status = "paused"
        campaign.last_error = f"Paused by {current_user.name}."
        flash("Sending paused.", "success")
    elif act == "resume" and campaign.status == "paused":
        campaign.status = "sending"
        campaign.last_error = None
        flash("Sending resumed.", "success")
    elif act == "cancel" and campaign.status in ("sending", "paused"):
        campaign.status = "cancelled"
        campaign.finished_at = utcnow()
        Message.query.filter_by(campaign_id=campaign.id, status="queued").update(
            {"status": "skipped", "error": "Campaign cancelled"}
        )
        flash("Campaign cancelled. Emails already sent can't be recalled.", "success")
    elif act == "duplicate":
        copy = Campaign(
            name=f"{campaign.name} (copy)",
            subject=campaign.subject,
            preview_text=campaign.preview_text,
            body_html=campaign.body_html,
            lists=list(campaign.lists),
            created_by_id=current_user.id,
        )
        db.session.add(copy)
        db.session.commit()
        flash("Campaign duplicated.", "success")
        return redirect(url_for("campaigns.edit", campaign_id=copy.id))
    elif act == "delete" and campaign.status in ("draft", "scheduled", "cancelled", "sent"):
        Event.query.filter_by(campaign_id=campaign.id).delete()
        db.session.delete(campaign)
        db.session.commit()
        flash("Campaign deleted.", "success")
        return redirect(url_for("campaigns.index"))
    else:
        flash("That action isn't available right now.", "error")
    db.session.commit()
    return redirect(request.referrer or url_for("campaigns.report", campaign_id=campaign.id))


@bp.route("/<int:campaign_id>")
@login_required
def report(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    if campaign.status == "draft":
        return redirect(url_for("campaigns.edit", campaign_id=campaign.id))
    return render_template(
        "campaigns/report.html",
        campaign=campaign,
        stats=campaign_stats([campaign.id])[campaign.id],
        timeline=campaign_timeline(campaign),
        links=top_links(campaign.id),
    )


@bp.route("/<int:campaign_id>/stats.json")
@login_required
def stats_json(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    return jsonify(
        status=campaign.status,
        last_error=campaign.last_error,
        stats=campaign_stats([campaign.id])[campaign.id],
        timeline=campaign_timeline(campaign),
    )


@bp.route("/<int:campaign_id>/recipients")
@login_required
def recipients(campaign_id):
    campaign = db.get_or_404(Campaign, campaign_id)
    filt = request.args.get("filter", "")
    query = Message.query.filter_by(campaign_id=campaign.id)
    filters = {
        "opened": Message.opened_at.isnot(None),
        "clicked": Message.clicked_at.isnot(None),
        "not_opened": Message.opened_at.is_(None) & Message.delivered_at.isnot(None),
        "bounced": Message.bounced_at.isnot(None),
        "complained": Message.complained_at.isnot(None),
        "unsubscribed": Message.unsubscribed_at.isnot(None),
        "failed": Message.status.in_(("failed", "skipped")),
    }
    if filt in filters:
        query = query.filter(filters[filt])
    page = query.order_by(Message.id).paginate(page=request.args.get("page", 1, type=int),
                                               per_page=100, error_out=False)
    return render_template("campaigns/recipients.html", campaign=campaign, page=page, filt=filt,
                           filters=list(filters))
