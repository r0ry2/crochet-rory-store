import os

# ==========================================
# 📁 BASE DIRECTORY
# ==========================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


class Config:

    # ==========================================
    # 🔐 SECRET KEY
    # ==========================================

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key"
    )

    # ==========================================
    # 🗄️ DATABASE
    # ==========================================

    DATABASE_URL = os.environ.get("DATABASE_URL")

    if DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace(
            "postgres://",
            "postgresql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or (
        "sqlite:///"
        + os.path.join(
            BASE_DIR,
            "data.sqlite"
        )
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==========================================
    # 📧 MAIL SETTINGS
    # ==========================================

    MAIL_SERVER = os.environ.get(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.environ.get(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USE_TLS = (
        os.environ.get(
            "MAIL_USE_TLS",
            "true"
        ).lower() == "true"
    )

    MAIL_USE_SSL = (
        os.environ.get(
            "MAIL_USE_SSL",
            "false"
        ).lower() == "true"
    )

    MAIL_USERNAME = os.environ.get(
        "MAIL_USERNAME",
        ""
    )

    MAIL_PASSWORD = os.environ.get(
        "MAIL_PASSWORD",
        ""
    )

    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER",
        "Crochet Rory"
    )