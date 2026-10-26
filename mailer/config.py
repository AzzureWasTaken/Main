import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'mailer.db'}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # CSV uploads up to 20 MB

    MAIL_BACKEND = os.environ.get("MAIL_BACKEND", "console").lower()
    AWS_REGION = os.environ.get("AWS_REGION", "eu-west-2")
    SES_CONFIGURATION_SET = os.environ.get("SES_CONFIGURATION_SET", "mailer")
    SES_CONTACT_LIST = os.environ.get("SES_CONTACT_LIST", "mailer-contacts")
    SES_TOPIC = os.environ.get("SES_TOPIC", "newsletter")
    SQS_QUEUE_NAME = os.environ.get("SQS_QUEUE_NAME", "mailer-events")

    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "8080"))
