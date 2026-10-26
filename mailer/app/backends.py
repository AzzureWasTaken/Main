"""Where emails actually go: Amazon SES, or a console "demo" backend that sends nothing."""

import json
import logging
import random
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone

log = logging.getLogger("mailer")


class SendError(Exception):
    """A single email failed (bad address, rejected content). Carry on with the rest."""


class RetryableError(Exception):
    """SES asked us to slow down. Wait and try the same email again."""


class FatalSendError(Exception):
    """Nothing will send until someone fixes the setup (credentials, sandbox, quota)."""


FATAL_CODES = {
    "AccountSuspendedException",
    "SendingPausedException",
    "MailFromDomainNotVerifiedException",
    "NotFoundException",
    "UnrecognizedClientException",
    "InvalidClientTokenId",
    "SignatureDoesNotMatch",
    "AccessDeniedException",
    "AccessDenied",
    "ExpiredTokenException",
}
RETRY_CODES = {"TooManyRequestsException", "Throttling", "ThrottlingException", "ServiceUnavailable"}


def _explain_fatal(message):
    if "not verified" in message.lower():
        return (
            f"{message} — If your SES account is still in the sandbox it can only send to "
            "verified addresses. Request production access in the SES console (see README)."
        )
    return message


class SESBackend:
    name = "ses"

    def __init__(self, config):
        import boto3

        self.config = config
        session = boto3.session.Session(region_name=config["AWS_REGION"])
        self.ses = session.client("sesv2")
        self.sqs = session.client("sqs")
        self._queue_url = None

    def send(self, *, from_addr, to, subject, html, text, reply_to=None, tags=None):
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

        kwargs = {
            "FromEmailAddress": from_addr,
            "Destination": {"ToAddresses": [to]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html, "Charset": "UTF-8"},
                        "Text": {"Data": text, "Charset": "UTF-8"},
                    },
                }
            },
            "ConfigurationSetName": self.config["SES_CONFIGURATION_SET"],
            "ListManagementOptions": {
                "ContactListName": self.config["SES_CONTACT_LIST"],
                "TopicName": self.config["SES_TOPIC"],
            },
            "EmailTags": [{"Name": k, "Value": str(v)} for k, v in (tags or {}).items()],
        }
        if reply_to:
            kwargs["ReplyToAddresses"] = [reply_to]
        try:
            return self.ses.send_email(**kwargs)["MessageId"]
        except NoCredentialsError as exc:
            raise FatalSendError("No AWS credentials found. Fill in AWS keys in .env.") from exc
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            message = exc.response.get("Error", {}).get("Message", str(exc))
            if "quota" in message.lower():
                raise FatalSendError(f"SES daily sending quota reached: {message}") from exc
            if code in RETRY_CODES:
                raise RetryableError(message) from exc
            if code in FATAL_CODES or "not verified" in message.lower():
                raise FatalSendError(_explain_fatal(f"{code}: {message}")) from exc
            raise SendError(f"{code}: {message}") from exc
        except BotoCoreError as exc:
            # Network trouble: worth retrying.
            raise RetryableError(str(exc)) from exc

    def max_send_rate(self):
        try:
            return float(self.ses.get_account()["SendQuota"]["MaxSendRate"])
        except Exception:  # noqa: BLE001 - fall back to the SES default
            return 1.0

    def account_status(self):
        """Summary for the settings page."""
        account = self.ses.get_account()
        quota = account.get("SendQuota", {})
        return {
            "production_access": account.get("ProductionAccessEnabled", False),
            "sending_enabled": account.get("SendingEnabled", False),
            "max_24h": int(quota.get("Max24HourSend", 0)),
            "sent_24h": int(quota.get("SentLast24Hours", 0)),
            "max_rate": quota.get("MaxSendRate", 0),
        }

    def _queue(self):
        if self._queue_url is None:
            self._queue_url = self.sqs.get_queue_url(QueueName=self.config["SQS_QUEUE_NAME"])["QueueUrl"]
        return self._queue_url

    def receive_events(self, wait_seconds=10):
        """Yield (event_dict, ack) pairs from the SQS queue SES publishes to."""
        response = self.sqs.receive_message(
            QueueUrl=self._queue(), MaxNumberOfMessages=10, WaitTimeSeconds=wait_seconds
        )
        for msg in response.get("Messages", []):
            body = json.loads(msg["Body"])
            if "Message" in body and "Type" in body:  # SNS envelope (raw delivery off)
                body = json.loads(body["Message"])

            def ack(handle=msg["ReceiptHandle"]):
                self.sqs.delete_message(QueueUrl=self._queue(), ReceiptHandle=handle)

            yield body, ack

    def unsubscribed_emails(self):
        """Everyone who opted out through SES's hosted unsubscribe page or header."""
        for page in self._list_contacts_pages():
            for contact in page.get("Contacts", []):
                prefs = contact.get("TopicPreferences", [])
                if contact.get("UnsubscribeAll") or any(
                    p.get("TopicName") == self.config["SES_TOPIC"] and p.get("SubscriptionStatus") == "OPT_OUT"
                    for p in prefs
                ):
                    yield contact["EmailAddress"].lower()

    def _list_contacts_pages(self):
        token = None
        while True:
            kwargs = {"ContactListName": self.config["SES_CONTACT_LIST"], "PageSize": 1000}
            if token:
                kwargs["NextToken"] = token
            page = self.ses.list_contacts(**kwargs)
            yield page
            token = page.get("NextToken")
            if not token:
                return


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class ConsoleBackend:
    """Demo mode: logs emails instead of sending, and invents realistic tracking events."""

    name = "console"
    _events = deque()
    _lock = threading.Lock()

    def __init__(self, config):
        self.config = config

    def send(self, *, from_addr, to, subject, html, text, reply_to=None, tags=None):
        message_id = f"demo-{uuid.uuid4()}"
        log.info("DEMO send to %s: %s", to, subject)
        now = datetime.now(timezone.utc)
        events = [("Send", now), ("Delivery", now + timedelta(seconds=2))]
        roll = random.random()
        if roll < 0.02:
            events = [("Send", now), ("Bounce", now + timedelta(seconds=2))]
        elif roll < 0.45:
            opened = now + timedelta(seconds=random.randint(5, 120))
            events.append(("Open", opened))
            if random.random() < 0.3:
                events.append(("Click", opened + timedelta(seconds=random.randint(2, 30))))
            if random.random() < 0.02:
                events.append(("Subscription", opened + timedelta(seconds=40)))
        with self._lock:
            for event_type, when in events:
                self._events.append(self._fake_event(event_type, when, message_id, to, tags or {}))
        return message_id

    def _fake_event(self, event_type, when, message_id, to, tags):
        event = {
            "eventType": event_type,
            "mail": {
                "messageId": message_id,
                "destination": [to],
                "tags": {k: [str(v)] for k, v in tags.items()},
            },
        }
        ts = _iso(when)
        if event_type == "Delivery":
            event["delivery"] = {"timestamp": ts}
        elif event_type == "Bounce":
            event["bounce"] = {"timestamp": ts, "bounceType": "Permanent", "bouncedRecipients": [{"emailAddress": to}]}
        elif event_type == "Open":
            event["open"] = {"timestamp": ts}
        elif event_type == "Click":
            event["click"] = {"timestamp": ts, "link": "https://example.com/demo-link"}
        elif event_type == "Subscription":
            event["subscription"] = {"timestamp": ts, "newTopicPreferences": {"unsubscribeAll": True}}
        else:
            event["send"] = {}
            event["mail"]["timestamp"] = ts
        return event

    def max_send_rate(self):
        return 50.0

    def account_status(self):
        return None

    def receive_events(self, wait_seconds=10):
        with self._lock:
            ready = list(self._events)
            self._events.clear()
        for event in ready:
            yield event, (lambda: None)

    def unsubscribed_emails(self):
        return iter(())


def get_backend(config):
    if config["MAIL_BACKEND"] == "ses":
        return SESBackend(config)
    return ConsoleBackend(config)
