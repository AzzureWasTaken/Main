"""Start Mailer: the web dashboard plus the background sender. Run with:  python run.py"""

import logging
import socket
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from waitress.server import create_server

from app import create_app
from app.worker import start_worker


def setup_logging():
    log_dir = Path(__file__).resolve().parent / "data"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(threadName)s] %(message)s")
    file_handler = RotatingFileHandler(log_dir / "mailer.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger = logging.getLogger("mailer")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console)


def lan_ip():
    """This computer's address on the local network (no traffic is actually sent)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main():
    setup_logging()
    app = create_app()
    host, port = app.config["HOST"], app.config["PORT"]

    # Binding the port first means a second copy fails here, before it can start sending too.
    server = create_server(app, host=host, port=port, threads=8)
    start_worker(app)

    print()
    print("  Mailer is running.")
    print(f"  On this computer:      http://localhost:{port}")
    if host == "0.0.0.0":
        print(f"  For your team (LAN):   http://{lan_ip()}:{port}")
    print(f"  Mode: {'LIVE - sending through Amazon SES' if app.config['MAIL_BACKEND'] == 'ses' else 'DEMO - no real emails are sent'}")
    print("  Keep this window open. Press Ctrl+C to stop.")
    print()
    try:
        server.run()
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
