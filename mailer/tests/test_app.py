import io
import re

import pytest

from app import create_app, db
from app.backends import ConsoleBackend, FatalSendError
from app.models import Campaign, Contact, ContactList, Message, Setting, User
from app.rendering import normalise_tags, render_email
from app.sender import send_campaign, start_campaign, start_due_campaigns
from app.tracking import apply_event, poll_events


@pytest.fixture
def app(tmp_path):
    app = create_app(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'test.db'}",
        WTF_CSRF_ENABLED=False,
        MAIL_BACKEND="console",
        TESTING=True,
    )
    ConsoleBackend._events.clear()
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, role="admin", email="admin@example.com"):
    if not User.query.filter_by(email=email).first():
        user = User(name=role.title(), email=email, role=role)
        user.set_password("correct-horse-battery")
        db.session.add(user)
        db.session.commit()
    resp = client.post("/login", data={"email": email, "password": "correct-horse-battery"})
    assert resp.status_code == 302


def configure_sender():
    Setting.set("from_name", "Test Co")
    Setting.set("from_email", "news@example.com")
    Setting.set("postal_address", "1 High Street\nLondon")
    db.session.commit()


def upload(client, csv_text, **form):
    data = {"file": (io.BytesIO(csv_text.encode("utf-8-sig")), "contacts.csv"), **form}
    return client.post("/contacts/import", data=data, content_type="multipart/form-data")


def test_first_run_creates_admin(client):
    assert client.get("/").status_code == 302
    assert client.get("/login").headers["Location"].endswith("/setup")
    resp = client.post("/setup", data={"name": "Ben", "email": "Ben@Example.com", "password": "long-enough-pw"})
    assert resp.status_code == 302
    assert User.query.one().role == "admin"
    assert client.get("/setup").status_code == 302  # disabled once a user exists
    assert client.get("/").status_code == 200


def test_csv_import_handles_headers_duplicates_and_suppression(client):
    login(client)
    db.session.add(Contact(email="gone@example.com", status="unsubscribed"))
    db.session.commit()
    csv_text = (
        "E-mail Address,First Name,Last Name,Company\n"
        "Jane@Example.com,Jane,Doe,Acme\n"
        "jane@example.com,Janet,,\n"
        "not-an-email,X,Y,\n"
        "gone@example.com,Gone,Person,\n"
        "sam@example.org,Sam,Lee,\n"
    )
    resp = upload(client, csv_text, new_list="Newsletter")
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert "Import complete" in page

    jane = Contact.query.filter_by(email="jane@example.com").one()
    assert jane.first_name == "Jane" and jane.fields == {"company": "Acme"}
    assert Contact.query.filter_by(email="gone@example.com").one().status == "unsubscribed"
    assert Contact.query.count() == 3
    assert ContactList.query.filter_by(name="Newsletter").one().contacts.count() == 3


def test_import_requires_email_column(client):
    login(client)
    resp = upload(client, "name,phone\nJane,123\n", new_list="Bad")
    assert resp.status_code == 302
    assert Contact.query.count() == 0


def make_campaign(n=20):
    lst = ContactList(name="All")
    db.session.add(lst)
    for i in range(n):
        lst.contacts.append(Contact(email=f"person{i}@example.com", first_name=f"P{i}"))
    campaign = Campaign(name="Hello", subject="Hi {{ first_name }}", body_html="<p>Hello {{ first_name }}</p>",
                        lists=[lst])
    db.session.add(campaign)
    db.session.commit()
    return campaign


def test_render_personalises_and_adds_footer(app):
    configure_sender()
    campaign = make_campaign(1)
    subject, html, text = render_email(campaign, Contact.query.first())
    assert subject == "Hi P0"
    assert "Hello P0" in html
    assert "{{amazonSESUnsubscribeUrl}}" in html and "{{amazonSESUnsubscribeUrl}}" in text
    assert "1 High Street, London" in html


def test_windows_line_endings_in_address(app):
    configure_sender()
    Setting.set("postal_address", "Acme Ltd\r\n1 High Street\r\n\r\nLondon")
    campaign = make_campaign(1)
    _, html, text = render_email(campaign, Contact.query.first())
    assert "Acme Ltd, 1 High Street, London" in html and "Acme Ltd, 1 High Street, London" in text


def test_template_escapes_contact_data(app):
    configure_sender()
    campaign = make_campaign(0)
    _, html, _ = render_email(campaign, {"email": "x@y.com", "first_name": "<script>bad()</script>"})
    assert "<script>bad()" not in html


def test_normalise_tags_unescapes_editor_output():
    assert normalise_tags('<p>{{ first_name or &quot;there&quot; }}</p>') == '<p>{{ first_name or "there" }}</p>'


def test_full_send_flow_with_tracking(app):
    configure_sender()
    campaign = make_campaign(20)
    # One contact is on the list but unsubscribed: must be left out.
    Contact.query.filter_by(email="person0@example.com").one().status = "unsubscribed"
    db.session.commit()

    start_campaign(campaign)
    assert campaign.status == "sending"
    assert campaign.messages.count() == 19

    backend = ConsoleBackend(app.config)
    send_campaign(backend, campaign.id)
    assert campaign.status == "sent"
    assert Message.query.filter_by(status="sent").count() == 19

    poll_events(backend)
    delivered = Message.query.filter(Message.delivered_at.isnot(None)).count()
    bounced = Message.query.filter(Message.bounced_at.isnot(None)).count()
    assert delivered + bounced == 19

    # Running the sender again must not resend anything.
    send_campaign(backend, campaign.id)
    assert Message.query.filter_by(status="sent").count() == 19


def test_bounce_complaint_and_unsubscribe_suppress_contacts(app):
    configure_sender()
    campaign = make_campaign(3)
    start_campaign(campaign)
    msgs = campaign.messages.order_by(Message.id).all()
    for i, m in enumerate(msgs):
        m.status, m.ses_message_id = "sent", f"ses-{i}"
    db.session.commit()

    apply_event({"eventType": "Bounce", "mail": {"messageId": "ses-0"},
                 "bounce": {"bounceType": "Permanent", "timestamp": "2026-01-01T10:00:00.000Z"}})
    apply_event({"eventType": "Complaint", "mail": {"messageId": "ses-1"}, "complaint": {}})
    apply_event({"eventType": "Subscription", "mail": {"messageId": "ses-2"},
                 "subscription": {"newTopicPreferences": {"unsubscribeAll": False,
                                  "topicSubscriptionStatus": [{"topicName": "newsletter", "subscriptionStatus": "OptOut"}]}}})
    db.session.commit()
    assert [m.contact.status for m in msgs] == ["bounced", "complained", "unsubscribed"]

    # Soft bounces don't suppress.
    contact = Contact(email="soft@example.com")
    db.session.add(contact)
    db.session.flush()
    db.session.add(Message(campaign_id=campaign.id, contact_id=contact.id, email=contact.email,
                           status="sent", ses_message_id="ses-soft"))
    apply_event({"eventType": "Bounce", "mail": {"messageId": "ses-soft"}, "bounce": {"bounceType": "Transient"}})
    db.session.commit()
    assert contact.status == "subscribed"


def test_event_matched_by_tag_when_id_not_saved_yet(app):
    campaign = make_campaign(1)
    start_campaign(campaign)
    message = campaign.messages.first()
    assert apply_event({"eventType": "Open", "mail": {"messageId": "unknown", "tags": {"message": [str(message.id)]}},
                        "open": {"timestamp": "2026-01-01T10:00:00Z"}})
    assert message.opened_at is not None


def test_fatal_error_pauses_campaign(app):
    configure_sender()
    campaign = make_campaign(3)
    start_campaign(campaign)

    class Broken(ConsoleBackend):
        def send(self, **kwargs):
            raise FatalSendError("Email address is not verified.")

    send_campaign(Broken(app.config), campaign.id)
    assert campaign.status == "paused"
    assert "not verified" in campaign.last_error
    assert Message.query.filter_by(status="queued").count() == 3


def test_send_page_schedules_and_worker_starts_it(client, app):
    login(client)
    configure_sender()
    campaign = make_campaign(2)
    resp = client.post(f"/campaigns/{campaign.id}/send", data={"mode": "now", "confirm": "yes"})
    assert resp.status_code == 302
    assert campaign.status == "scheduled"
    start_due_campaigns()
    assert campaign.status == "sending"


def test_send_requires_postal_address(client):
    login(client)
    Setting.set("from_email", "news@example.com")
    db.session.commit()
    campaign = make_campaign(2)
    client.post(f"/campaigns/{campaign.id}/send", data={"mode": "now", "confirm": "yes"})
    assert campaign.status == "draft"


def test_campaign_editor_and_report_pages(client, app):
    login(client)
    configure_sender()
    lst = ContactList(name="Main")
    lst.contacts.append(Contact(email="a@example.com", first_name="Ann"))
    db.session.add(lst)
    db.session.commit()

    resp = client.post("/campaigns/new", data={
        "name": "Nov", "subject": "News for {{ first_name }}", "preview_text": "",
        "body_html": "<p>Hi {{ first_name or &quot;there&quot; }}</p>", "list_ids": [str(lst.id)], "next": "save",
    })
    assert resp.status_code == 302
    campaign = Campaign.query.one()
    assert campaign.body_html == '<p>Hi {{ first_name or "there" }}</p>'
    assert "Hi Ann" in client.get(f"/campaigns/{campaign.id}/preview").get_data(as_text=True)

    bad = client.post(f"/campaigns/{campaign.id}/edit", data={
        "name": "Nov", "subject": "Broken {{ first_name", "body_html": "<p>x</p>", "next": "save"})
    assert bad.status_code == 200 and "Template error" in bad.get_data(as_text=True)

    assert client.post(f"/campaigns/{campaign.id}/test", data={"emails": "me@example.com"}).status_code == 302
    start_campaign(campaign)
    send_campaign(ConsoleBackend(app.config), campaign.id)
    poll_events(ConsoleBackend(app.config))
    for url in ("/", "/campaigns/", f"/campaigns/{campaign.id}", f"/campaigns/{campaign.id}/stats.json",
                f"/campaigns/{campaign.id}/recipients?filter=opened", "/contacts/", "/contacts/lists",
                "/settings/", "/users", "/account"):
        assert client.get(url).status_code == 200, url


def test_viewer_cannot_edit(client):
    login(client, role="viewer", email="viewer@example.com")
    assert client.get("/").status_code == 200
    assert client.get("/campaigns/new").status_code == 403
    assert client.get("/contacts/import").status_code == 403
    assert client.get("/settings/").status_code == 403


def test_schedule_time_converted_to_utc(client, app):
    login(client)
    configure_sender()
    campaign = make_campaign(1)
    client.post(f"/campaigns/{campaign.id}/send",
                data={"mode": "schedule", "scheduled_at": "2099-06-01T09:30", "confirm": "yes"})
    assert campaign.status == "scheduled"
    assert campaign.scheduled_at.year == 2099


def test_delete_contact_and_list_keep_history(client, app):
    login(client)
    configure_sender()
    campaign = make_campaign(2)
    start_campaign(campaign)
    send_campaign(ConsoleBackend(app.config), campaign.id)
    contact = Contact.query.first()
    assert client.post(f"/contacts/{contact.id}/status", data={"action": "delete"}).status_code == 302
    assert campaign.messages.count() == 2
    lst = ContactList.query.one()
    client.post(f"/contacts/lists/{lst.id}/delete", data={"confirm": "yes"})
    assert ContactList.query.count() == 0
    assert client.post(f"/campaigns/{campaign.id}/action", data={"action": "delete"}).status_code == 302
    assert Campaign.query.count() == 0
