import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" +
        os.path.join(BASE_DIR, "data.sqlite")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ===== إعدادات البريد =====
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = "noni200217noni@gmail.com"
    MAIL_PASSWORD = "ingf nqmw reno qnbi"
    MAIL_DEFAULT_SENDER = "Crochet Rory <noni200217noni@gmail.com>"