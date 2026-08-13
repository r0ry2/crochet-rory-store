import os
from dotenv import load_dotenv

# ==========================================
# 📁 BASE DIRECTORY
# ==========================================

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

# تحميل متغيرات .env
load_dotenv()


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

    DATABASE_URL = os.environ.get(
        "DATABASE_URL"
    )

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
# 📧 GMAIL SMTP
# ==========================================

MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587

MAIL_USE_TLS = True
MAIL_USE_SSL = False

MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

MAIL_DEFAULT_SENDER = os.environ.get(
    "MAIL_DEFAULT_SENDER",
    MAIL_USERNAME
)

MAIL_TIMEOUT = 30