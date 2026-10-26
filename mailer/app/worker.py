"""Background threads that run alongside the web dashboard."""

import logging
import threading
import time

from . import db
from .backends import get_backend
from .models import Campaign
from .sender import send_campaign, start_due_campaigns
from .tracking import poll_events, sync_unsubscribes

log = logging.getLogger("mailer")

SENDER_TICK = 5  # seconds between checks for scheduled campaigns
UNSUBSCRIBE_SYNC_EVERY = 30 * 60


def _sender_loop(app, stop):
    backend = get_backend(app.config)
    while not stop.is_set():
        try:
            with app.app_context():
                start_due_campaigns()
                for (campaign_id,) in db.session.query(Campaign.id).filter_by(status="sending").all():
                    send_campaign(backend, campaign_id, should_stop=stop.is_set)
                db.session.remove()
        except Exception:  # noqa: BLE001 - never let the thread die
            log.exception("Sender loop error")
        stop.wait(SENDER_TICK)


def _events_loop(app, stop):
    backend = get_backend(app.config)
    last_sync = 0.0
    while not stop.is_set():
        try:
            with app.app_context():
                poll_events(backend, wait_seconds=10)
                if time.monotonic() - last_sync > UNSUBSCRIBE_SYNC_EVERY:
                    changed = sync_unsubscribes(backend)
                    if changed:
                        log.info("Synced %s unsubscribes from SES", changed)
                    last_sync = time.monotonic()
                db.session.remove()
        except Exception:  # noqa: BLE001
            log.exception("Event loop error")
            stop.wait(30)  # e.g. no network or AWS not set up yet
        if app.config["MAIL_BACKEND"] != "ses":
            stop.wait(3)  # demo backend returns immediately; don't spin


def start_worker(app):
    stop = threading.Event()
    for target, name in ((_sender_loop, "sender"), (_events_loop, "events")):
        threading.Thread(target=target, args=(app, stop), name=name, daemon=True).start()
    return stop
