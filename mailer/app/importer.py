import csv
import io
import re
from dataclasses import dataclass, field

from . import db
from .models import Contact, ContactList

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

EMAIL_HEADERS = {"email", "e-mail", "emailaddress", "e-mailaddress", "mail"}
FIRST_HEADERS = {"firstname", "first", "givenname", "forename"}
LAST_HEADERS = {"lastname", "last", "surname", "familyname"}
FULL_NAME_HEADERS = {"name", "fullname"}


def _squash(header):
    return re.sub(r"[\s_]+", "", (header or "").strip().lower())


def _field_key(header):
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


@dataclass
class ImportResult:
    added: int = 0
    updated: int = 0
    suppressed_kept: int = 0
    invalid: int = 0
    duplicates: int = 0
    invalid_examples: list = field(default_factory=list)


def decode_upload(raw: bytes) -> str:
    # Excel on Windows saves "CSV UTF-8" with a BOM, or plain CSV as cp1252.
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read the file's text encoding.")


def import_csv(text: str, target_list: ContactList) -> ImportResult:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("The file is empty.")

    email_col = first_col = last_col = full_col = None
    extra_cols = []
    for header in reader.fieldnames:
        key = _squash(header)
        if key in EMAIL_HEADERS and email_col is None:
            email_col = header
        elif key in FIRST_HEADERS and first_col is None:
            first_col = header
        elif key in LAST_HEADERS and last_col is None:
            last_col = header
        elif key in FULL_NAME_HEADERS and full_col is None:
            full_col = header
        elif header and header.strip():
            extra_cols.append(header)
    if email_col is None:
        raise ValueError(
            "No email column found. Name one of the columns 'email' "
            f"(found: {', '.join(h for h in reader.fieldnames if h)})."
        )

    existing = {c.email: c for c in Contact.query.all()}
    member_ids = {c.id for c in target_list.contacts}
    seen = set()
    result = ImportResult()

    for row in reader:
        email = (row.get(email_col) or "").strip().lower()
        if not EMAIL_RE.match(email):
            if email or any((v or "").strip() for v in row.values() if isinstance(v, str)):
                result.invalid += 1
                if len(result.invalid_examples) < 5:
                    result.invalid_examples.append(email or "(blank)")
            continue
        if email in seen:
            result.duplicates += 1
            continue
        seen.add(email)

        first = (row.get(first_col) or "").strip() if first_col else ""
        last = (row.get(last_col) or "").strip() if last_col else ""
        if full_col and not (first or last):
            parts = (row.get(full_col) or "").strip().split(None, 1)
            first = parts[0] if parts else ""
            last = parts[1] if len(parts) > 1 else ""
        extras = {
            _field_key(col): (row.get(col) or "").strip()
            for col in extra_cols
            if (row.get(col) or "").strip()
        }

        contact = existing.get(email)
        if contact is None:
            contact = Contact(email=email, first_name=first, last_name=last)
            contact.fields = extras
            db.session.add(contact)
            existing[email] = contact
            result.added += 1
        else:
            if first:
                contact.first_name = first
            if last:
                contact.last_name = last
            if extras:
                contact.fields = {**contact.fields, **extras}
            if contact.status != "subscribed":
                # Never re-subscribe someone who unsubscribed, bounced or complained.
                result.suppressed_kept += 1
            else:
                result.updated += 1
        if contact.id is None or contact.id not in member_ids:
            target_list.contacts.append(contact)

    db.session.commit()
    return result
