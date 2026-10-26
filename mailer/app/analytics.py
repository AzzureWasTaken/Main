from datetime import timedelta

from sqlalchemy import case, distinct, func

from . import db
from .models import Campaign, Event, Message


def _count(condition):
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


def campaign_stats(campaign_ids):
    """{campaign_id: {...counts and rates...}} for the given campaigns."""
    if not campaign_ids:
        return {}
    rows = (
        db.session.query(
            Message.campaign_id,
            func.count(Message.id),
            _count(Message.status == "queued"),
            _count(Message.status == "sent"),
            _count(Message.status == "failed"),
            _count(Message.status == "skipped"),
            _count(Message.delivered_at.isnot(None)),
            _count(Message.opened_at.isnot(None)),
            _count(Message.clicked_at.isnot(None)),
            _count(Message.bounce_type == "Permanent"),
            _count(Message.bounced_at.isnot(None)),
            _count(Message.complained_at.isnot(None)),
            _count(Message.unsubscribed_at.isnot(None)),
            func.coalesce(func.sum(Message.open_count), 0),
            func.coalesce(func.sum(Message.click_count), 0),
        )
        .filter(Message.campaign_id.in_(campaign_ids))
        .group_by(Message.campaign_id)
        .all()
    )
    keys = (
        "recipients queued sent failed skipped delivered opened clicked "
        "hard_bounced bounced complained unsubscribed total_opens total_clicks"
    ).split()
    stats = {cid: dict.fromkeys(keys, 0) for cid in campaign_ids}
    for row in rows:
        stats[row[0]] = dict(zip(keys, (int(v) for v in row[1:])))
    for s in stats.values():
        s["open_rate"] = _rate(s["opened"], s["delivered"])
        s["click_rate"] = _rate(s["clicked"], s["delivered"])
        s["click_to_open"] = _rate(s["clicked"], s["opened"])
        s["delivery_rate"] = _rate(s["delivered"], s["sent"])
        s["bounce_rate"] = _rate(s["bounced"], s["sent"])
        s["complaint_rate"] = _rate(s["complained"], s["delivered"])
        s["unsubscribe_rate"] = _rate(s["unsubscribed"], s["delivered"])
        s["progress"] = _rate(s["recipients"] - s["queued"], s["recipients"])
    return stats


def _rate(numerator, denominator):
    return round(numerator / denominator * 100, 1) if denominator else None


def campaign_timeline(campaign, hours=72):
    """Hourly unique opens and clicks for the first `hours` after sending started."""
    if not campaign.started_at:
        return {"labels": [], "opens": [], "clicks": []}
    start = campaign.started_at.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    buckets = {}
    for column, key in ((Message.opened_at, "opens"), (Message.clicked_at, "clicks")):
        hour = func.strftime("%Y-%m-%d %H:00", column)
        rows = (
            db.session.query(hour, func.count())
            .filter(Message.campaign_id == campaign.id, column.isnot(None), column < end)
            .group_by(hour)
            .all()
        )
        for hour, n in rows:
            buckets.setdefault(hour, {"opens": 0, "clicks": 0})[key] = n

    labels, opens, clicks = [], [], []
    last_hour = max(buckets) if buckets else start.strftime("%Y-%m-%d %H:00")
    t = start
    while t.strftime("%Y-%m-%d %H:00") <= last_hour and t < end:
        key = t.strftime("%Y-%m-%d %H:00")
        labels.append(t.isoformat() + "Z")
        opens.append(buckets.get(key, {}).get("opens", 0))
        clicks.append(buckets.get(key, {}).get("clicks", 0))
        t += timedelta(hours=1)
    return {"labels": labels, "opens": opens, "clicks": clicks}


def top_links(campaign_id, limit=10):
    return (
        db.session.query(Event.detail, func.count(distinct(Event.message_id)), func.count(Event.id))
        .filter(Event.campaign_id == campaign_id, Event.type == "Click", Event.detail.isnot(None))
        .group_by(Event.detail)
        .order_by(func.count(distinct(Event.message_id)).desc())
        .limit(limit)
        .all()
    )


def recent_sent_campaigns(limit=10):
    return (
        Campaign.query.filter(Campaign.status.in_(("sending", "paused", "sent")))
        .order_by(Campaign.started_at.desc())
        .limit(limit)
        .all()
    )
