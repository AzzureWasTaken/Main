import html
import re
from html.parser import HTMLParser

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from .models import Setting

# SES replaces this placeholder with a hosted, per-recipient unsubscribe page.
SES_UNSUBSCRIBE_PLACEHOLDER = "{{amazonSESUnsubscribeUrl}}"

_env = SandboxedEnvironment(autoescape=True)
_text_env = SandboxedEnvironment(autoescape=False)

SAMPLE_CONTACT = {
    "email": "jane.doe@example.com",
    "first_name": "Jane",
    "last_name": "Doe",
}

LAYOUT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f4f5f7;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preview}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f5f7;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:8px;">
<tr><td style="padding:32px;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6;color:#1f2933;">
{body}
</td></tr>
</table>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:16px 32px;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#7b8794;text-align:center;">
{footer}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def template_context(contact):
    """Variables available in subject and body, e.g. {{ first_name }}."""
    if isinstance(contact, dict):
        data = dict(contact)
    else:
        data = dict(contact.fields)
        data.update(email=contact.email, first_name=contact.first_name or "", last_name=contact.last_name or "")
    data.setdefault("first_name", "")
    data.setdefault("last_name", "")
    data["name"] = " ".join(p for p in (data["first_name"], data["last_name"]) if p)
    return data


_TAG_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.S)


def normalise_tags(source):
    """Undo HTML escaping the visual editor applies inside {{ }} tags (e.g. &quot; -> ")."""
    return _TAG_RE.sub(lambda m: html.unescape(m.group(0)).replace("\xa0", " "), source or "")


def validate_template(source):
    """Return an error message if the subject or body has broken {{ }} tags."""
    try:
        _env.from_string(source)
    except TemplateError as exc:
        return f"Template error: {exc}"
    return None


def _postal_address():
    """The address as one line: 'Acme Ltd, 1 High St, London'. Handles Windows line endings."""
    return ", ".join(line.strip() for line in Setting.get("postal_address").splitlines() if line.strip())


def _footer_html(unsubscribe_url):
    sender = Setting.get("from_name") or "us"
    address = _postal_address()
    parts = [f"You're receiving this email because you subscribed to updates from {html.escape(sender)}."]
    if address:
        parts.append(html.escape(address))
    parts.append(f'<a href="{unsubscribe_url}" style="color:#7b8794;">Unsubscribe</a>')
    return "<br>".join(parts)


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li", "table"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._href = None

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")
        if tag == "a":
            self._href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.parts.append(f" ({self._href})")
            self._href = None
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(source):
    parser = _TextExtractor()
    parser.feed(source)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def render_email(campaign, contact, unsubscribe_url=SES_UNSUBSCRIBE_PLACEHOLDER):
    """Build (subject, html, text) for one recipient."""
    ctx = template_context(contact)
    subject = _text_env.from_string(campaign.subject).render(ctx).strip()
    body = _env.from_string(campaign.body_html).render(ctx, unsubscribe_url=Markup(unsubscribe_url))
    preview = _text_env.from_string(campaign.preview_text or "").render(ctx)
    full_html = LAYOUT.format(
        subject=html.escape(subject),
        preview=html.escape(preview),
        body=body,
        footer=_footer_html(unsubscribe_url),
    )
    address = _postal_address()
    text =html_to_text(body) + f"\n\n--\nUnsubscribe: {unsubscribe_url}"
    if address:
        text += f"\n{address}"
    return subject, full_html, text
