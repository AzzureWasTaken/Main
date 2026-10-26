from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def editor_required(view):
    """Admins and editors can change things; viewers can only look."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.can_edit:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
