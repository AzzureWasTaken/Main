from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db
from .models import ROLES, Campaign, User
from .permissions import admin_required

bp = Blueprint("auth", __name__)

MIN_PASSWORD_LENGTH = 10


def _password_problem(password):
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters."
    return None


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """First-run page: create the first admin. Disabled once any user exists."""
    if User.query.count():
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        problem = _password_problem(password) or (None if name and email else "All fields are required.")
        if problem:
            flash(problem, "error")
        else:
            user = User(name=name, email=email, role="admin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Admin account created. Next, fill in your sender settings.", "success")
            return redirect(url_for("settings.index"))
    return render_template("auth/setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if not User.query.count():
        return redirect(url_for("auth.setup"))
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next", "")
            # Only follow relative redirects, never to another site.
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard.index")
            return redirect(next_url)
        flash("Incorrect email or password.", "error")
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        if not current_user.check_password(request.form.get("current_password", "")):
            flash("Your current password is incorrect.", "error")
        else:
            new = request.form.get("new_password", "")
            problem = _password_problem(new)
            if problem:
                flash(problem, "error")
            else:
                current_user.set_password(new)
                db.session.commit()
                flash("Password updated.", "success")
        return redirect(url_for("auth.account"))
    return render_template("auth/account.html")


@bp.route("/users")
@admin_required
def users():
    return render_template("auth/users.html", users=User.query.order_by(User.name).all(), roles=ROLES)


@bp.route("/users/new", methods=["POST"])
@admin_required
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "editor")
    problem = _password_problem(password)
    if not name or not email or role not in ROLES:
        problem = "Name, email and a valid role are required."
    elif User.query.filter_by(email=email).first():
        problem = "A user with that email already exists."
    if problem:
        flash(problem, "error")
    else:
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f"Added {name}. Share their password with them privately.", "success")
    return redirect(url_for("auth.users"))


@bp.route("/users/<int:user_id>", methods=["POST"])
@admin_required
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    action = request.form.get("action")
    if action == "role":
        role = request.form.get("role")
        if role not in ROLES:
            flash("Unknown role.", "error")
        elif user.id == current_user.id and role != "admin":
            flash("You can't remove your own admin access.", "error")
        else:
            user.role = role
            flash(f"{user.name} is now {role}.", "success")
    elif action == "password":
        password = request.form.get("password", "")
        problem = _password_problem(password)
        if problem:
            flash(problem, "error")
        else:
            user.set_password(password)
            flash(f"Password reset for {user.name}.", "success")
    elif action == "delete":
        if user.id == current_user.id:
            flash("You can't delete your own account.", "error")
        else:
            Campaign.query.filter_by(created_by_id=user.id).update({"created_by_id": None})
            db.session.delete(user)
            flash(f"Removed {user.name}.", "success")
    db.session.commit()
    return redirect(url_for("auth.users"))
