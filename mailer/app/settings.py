from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from . import db
from .backends import get_backend
from .models import Setting
from .permissions import admin_required

bp = Blueprint("settings", __name__, url_prefix="/settings")

FIELDS = {
    "from_name": "From name",
    "from_email": "From email address",
    "reply_to": "Reply-to address",
    "postal_address": "Postal address",
}


@bp.route("/", methods=["GET", "POST"])
@admin_required
def index():
    if request.method == "POST":
        for key in FIELDS:
            Setting.set(key, request.form.get(key, "").strip())
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("settings.index"))

    values = {key: Setting.get(key) for key in FIELDS}
    status, status_error = None, None
    if request.args.get("check"):
        try:
            status = get_backend(current_app.config).account_status()
        except Exception as exc:  # noqa: BLE001 - show any AWS problem to the admin
            status_error = str(exc)
    return render_template(
        "settings.html",
        values=values,
        backend=current_app.config["MAIL_BACKEND"],
        region=current_app.config["AWS_REGION"],
        status=status,
        status_error=status_error,
        checked=bool(request.args.get("check")),
    )
