from datetime import timezone
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):
    # WAL lets the dashboard read while the background sender writes.
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_app(config_object="config.Config", **overrides):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.update(overrides)

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
        Path(app.config["SQLALCHEMY_DATABASE_URI"][len("sqlite:///"):]).parent.mkdir(
            parents=True, exist_ok=True
        )

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from .auth import bp as auth_bp
    from .campaigns import bp as campaigns_bp
    from .contacts import bp as contacts_bp
    from .dashboard import bp as dashboard_bp
    from .settings import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(campaigns_bp)
    app.register_blueprint(settings_bp)

    register_filters(app)
    register_errors(app)

    with app.app_context():
        db.create_all()

    return app


def register_errors(app):
    from flask import render_template
    from flask_wtf.csrf import CSRFError

    pages = {
        403: ("Not allowed", "Your role doesn't allow this. Ask an admin if you need access."),
        404: ("Not found", "That page doesn't exist."),
        413: ("File too large", "Uploads are limited to 20 MB. Split the CSV into smaller files."),
    }
    for code, (title, message) in pages.items():
        app.register_error_handler(
            code, lambda e, c=code, t=title, m=message: (render_template("error.html", code=c, title=t, message=m), c)
        )

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template("error.html", code=400, title="Form expired",
                               message="The page was open too long. Go back, refresh and try again."), 400


def register_filters(app):
    @app.template_filter("localtime")
    def localtime(value, fmt="%d %b %Y, %H:%M"):
        """Show a stored UTC timestamp in the host computer's time zone."""
        if value is None:
            return "—"
        return value.replace(tzinfo=timezone.utc).astimezone().strftime(fmt)

    @app.template_filter("pct")
    def pct(numerator, denominator):
        if not denominator:
            return "—"
        return f"{numerator / denominator * 100:.1f}%"

    @app.template_filter("num")
    def num(value):
        return f"{value or 0:,}"
