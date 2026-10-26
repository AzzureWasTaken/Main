from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, or_

from . import db
from .importer import decode_upload, import_csv
from .models import (
    CONTACT_STATUSES,
    Campaign,
    Contact,
    ContactList,
    Message,
    campaign_lists,
    list_members,
)
from .permissions import editor_required

bp = Blueprint("contacts", __name__, url_prefix="/contacts")

PER_PAGE = 50


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    list_id = request.args.get("list", type=int)

    query = Contact.query
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Contact.email.like(like),
                func.lower(Contact.first_name).like(like),
                func.lower(Contact.last_name).like(like),
            )
        )
    if status in CONTACT_STATUSES:
        query = query.filter(Contact.status == status)
    if list_id:
        query = query.join(list_members).filter(list_members.c.list_id == list_id)

    page = query.order_by(Contact.created_at.desc(), Contact.id.desc()).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=PER_PAGE,
        error_out=False,
    )
    counts = dict(db.session.query(Contact.status, func.count()).group_by(Contact.status).all())
    return render_template(
        "contacts/index.html",
        page=page,
        q=q,
        status=status,
        list_id=list_id,
        lists=ContactList.query.order_by(ContactList.name).all(),
        counts=counts,
        statuses=CONTACT_STATUSES,
    )


@bp.route("/import", methods=["GET", "POST"])
@editor_required
def import_contacts():
    lists = ContactList.query.order_by(ContactList.name).all()
    if request.method == "POST":
        upload = request.files.get("file")
        new_list_name = request.form.get("new_list", "").strip()
        list_id = request.form.get("list_id", type=int)

        if not upload or not upload.filename:
            flash("Choose a CSV file to import.", "error")
            return redirect(request.url)
        if new_list_name:
            target = ContactList.query.filter_by(name=new_list_name).first()
            if target is None:
                target = ContactList(name=new_list_name)
                db.session.add(target)
                db.session.flush()
        else:
            target = db.session.get(ContactList, list_id) if list_id else None
        if target is None:
            flash("Pick a list or type a name for a new one.", "error")
            return redirect(request.url)

        try:
            result = import_csv(decode_upload(upload.read()), target)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return redirect(request.url)
        return render_template("contacts/import_done.html", result=result, target=target)
    return render_template("contacts/import.html", lists=lists)


@bp.route("/<int:contact_id>/status", methods=["POST"])
@editor_required
def set_status(contact_id):
    contact = db.get_or_404(Contact, contact_id)
    action = request.form.get("action")
    if action == "unsubscribe":
        contact.suppress("unsubscribed")
        flash(f"{contact.email} unsubscribed.", "success")
    elif action == "delete":
        # Keep past campaign stats; just detach them from the deleted contact.
        Message.query.filter_by(contact_id=contact.id).update({"contact_id": None})
        db.session.delete(contact)
        flash(f"{contact.email} deleted.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("contacts.index"))


@bp.route("/lists", methods=["GET", "POST"])
@login_required
def lists():
    if request.method == "POST":
        return _create_list()
    rows = (
        db.session.query(
            ContactList,
            func.count(Contact.id).filter(Contact.status == "subscribed"),
            func.count(Contact.id),
        )
        .outerjoin(list_members, list_members.c.list_id == ContactList.id)
        .outerjoin(Contact, Contact.id == list_members.c.contact_id)
        .group_by(ContactList.id)
        .order_by(ContactList.name)
        .all()
    )
    return render_template("contacts/lists.html", rows=rows)


@editor_required
def _create_list():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Give the list a name.", "error")
    elif ContactList.query.filter_by(name=name).first():
        flash("A list with that name already exists.", "error")
    else:
        db.session.add(ContactList(name=name))
        db.session.commit()
        flash(f"Created list “{name}”.", "success")
    return redirect(url_for("contacts.lists"))


@bp.route("/lists/<int:list_id>/delete", methods=["POST"])
@editor_required
def delete_list(list_id):
    contact_list = db.get_or_404(ContactList, list_id)
    pending = [c for c in Campaign.query.filter(Campaign.status.in_(("draft", "scheduled", "sending")))
               if contact_list in c.lists]
    if pending:
        flash(f"“{pending[0].name}” still uses this list. Change that campaign first.", "error")
        return redirect(url_for("contacts.lists"))
    if contact_list.contacts.count() and request.form.get("confirm") != "yes":
        flash("Tick the confirmation box to delete a list that has contacts.", "error")
        return redirect(url_for("contacts.lists"))
    db.session.execute(campaign_lists.delete().where(campaign_lists.c.list_id == list_id))
    db.session.execute(list_members.delete().where(list_members.c.list_id == list_id))
    db.session.delete(contact_list)
    db.session.commit()
    flash(f"Deleted list “{contact_list.name}”. The contacts themselves were kept.", "success")
    return redirect(url_for("contacts.lists"))
