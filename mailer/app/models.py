import json
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


def utcnow():
    """Naive UTC timestamp; everything in the database is stored in UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLES = ("admin", "editor", "viewer")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="editor")
    created_at = db.Column(db.DateTime, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def can_edit(self):
        return self.role in ("admin", "editor")

    @property
    def is_admin(self):
        return self.role == "admin"


class Setting(db.Model):
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")

    @staticmethod
    def get(key, default=""):
        row = db.session.get(Setting, key)
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = db.session.get(Setting, key)
        if row is None:
            db.session.add(Setting(key=key, value=value))
        else:
            row.value = value


list_members = db.Table(
    "list_members",
    db.Column("list_id", db.Integer, db.ForeignKey("contact_list.id"), primary_key=True),
    db.Column("contact_id", db.Integer, db.ForeignKey("contact.id"), primary_key=True),
)

campaign_lists = db.Table(
    "campaign_lists",
    db.Column("campaign_id", db.Integer, db.ForeignKey("campaign.id"), primary_key=True),
    db.Column("list_id", db.Integer, db.ForeignKey("contact_list.id"), primary_key=True),
)


class ContactList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    contacts = db.relationship(
        "Contact", secondary=list_members, back_populates="lists", lazy="dynamic"
    )


CONTACT_STATUSES = ("subscribed", "unsubscribed", "bounced", "complained")


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(120), default="")
    last_name = db.Column(db.String(120), default="")
    fields_json = db.Column(db.Text, default="{}")
    status = db.Column(db.String(20), nullable=False, default="subscribed", index=True)
    status_changed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=utcnow)
    lists = db.relationship("ContactList", secondary=list_members, back_populates="contacts")

    @property
    def fields(self):
        try:
            return json.loads(self.fields_json or "{}")
        except ValueError:
            return {}

    @fields.setter
    def fields(self, value):
        self.fields_json = json.dumps(value)

    def suppress(self, status):
        """Stop emailing this contact. A complaint outranks a bounce or unsubscribe."""
        rank = {"subscribed": 0, "unsubscribed": 1, "bounced": 2, "complained": 3}
        if rank[status] > rank[self.status]:
            self.status = status
            self.status_changed_at = utcnow()


CAMPAIGN_STATUSES = ("draft", "scheduled", "sending", "paused", "sent", "cancelled")


class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(300), nullable=False, default="")
    preview_text = db.Column(db.String(300), default="")
    body_html = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    scheduled_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_by = db.relationship("User")
    lists = db.relationship("ContactList", secondary=campaign_lists)
    messages = db.relationship(
        "Message", back_populates="campaign", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def editable(self):
        return self.status in ("draft", "scheduled")


class Message(db.Model):
    """One email to one recipient within a campaign, plus everything that happened to it."""

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False, index=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contact.id"), index=True)
    email = db.Column(db.String(255), nullable=False)
    token = db.Column(db.String(32), unique=True, default=lambda: secrets.token_hex(16))
    # queued -> sent | failed | skipped
    status = db.Column(db.String(20), nullable=False, default="queued", index=True)
    error = db.Column(db.Text)
    ses_message_id = db.Column(db.String(120), unique=True, index=True)
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    open_count = db.Column(db.Integer, default=0)
    clicked_at = db.Column(db.DateTime)
    click_count = db.Column(db.Integer, default=0)
    bounced_at = db.Column(db.DateTime)
    bounce_type = db.Column(db.String(40))
    complained_at = db.Column(db.DateTime)
    unsubscribed_at = db.Column(db.DateTime)

    campaign = db.relationship("Campaign", back_populates="messages")
    contact = db.relationship("Contact")

    __table_args__ = (db.UniqueConstraint("campaign_id", "contact_id"),)


class Event(db.Model):
    """Raw tracking events, kept for timelines and click-by-link reports."""

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey("message.id"), index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), index=True)
    type = db.Column(db.String(30), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=utcnow)
    detail = db.Column(db.Text)
