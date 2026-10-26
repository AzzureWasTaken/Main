from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from . import db
from .analytics import campaign_stats, recent_sent_campaigns
from .models import Campaign, Contact

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    contact_counts = dict(db.session.query(Contact.status, func.count()).group_by(Contact.status).all())
    recent = recent_sent_campaigns(limit=12)
    stats = campaign_stats([c.id for c in recent])

    totals = {k: sum(s[k] for s in stats.values()) for k in ("sent", "delivered", "opened", "clicked", "bounced", "unsubscribed")}
    chart = {
        "labels": [c.name for c in reversed(recent)],
        "open_rate": [stats[c.id]["open_rate"] or 0 for c in reversed(recent)],
        "click_rate": [stats[c.id]["click_rate"] or 0 for c in reversed(recent)],
    }
    upcoming = (
        Campaign.query.filter(Campaign.status.in_(("scheduled", "sending", "paused")))
        .order_by(Campaign.scheduled_at)
        .all()
    )
    return render_template(
        "dashboard.html",
        contact_counts=contact_counts,
        recent=recent,
        stats=stats,
        totals=totals,
        chart=chart,
        upcoming=upcoming,
    )
