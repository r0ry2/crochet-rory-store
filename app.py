import os
from dotenv import load_dotenv

from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_babel import Babel
from flask import session

from config import Config

from models import (
    db,
    Product,
    Order,
    OrderItem,
    User,
    Message,
    Cart,
    Wishlist,
    ShippingMethod,
    Coupon,
    Notification
)

# ==========================================
# 🔎 DEBUG - CHECK LOADED PRODUCT MODEL
# ==========================================

print("🔥 MODELS FILE:", Product.__module__)
print("🔥 PRODUCT COLUMNS:")
print(Product.__table__.columns.keys())

# ==========================================
# Load Environment Variables
# ==========================================

load_dotenv()

# ==========================================
# Create Flask App
# ==========================================

app = Flask(__name__)
app.config.from_object(Config)

app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_SUPPORTED_LOCALES"] = ["en", "ar"]


def get_locale():
    return session.get("language", "en")


babel = Babel(
    app,
    locale_selector=get_locale
)


@app.context_processor
def inject_locale():
    return {
        "current_lang": session.get("language", "en")
    }


# ==========================================
# Secret Key & Database
# ==========================================

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "supersecretkey"
)

database_url = os.getenv("DATABASE_URL")

if database_url:
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.sqlite"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# ==========================================
# Mail
# ==========================================

mail = Mail(app)


# ==========================================
# Database
# ==========================================

db.init_app(app)

migrate = Migrate(
    app,
    db
)

# ==========================================
# Database
# ==========================================

db.init_app(app)

migrate = Migrate(
    app,
    db
)


with app.app_context():

    db.create_all()

    # ==========================================
    # 🔧 Update existing Product table
    # Add new columns if they don't exist
    # ==========================================

    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)

    product_columns = {
        column["name"]
        for column in inspector.get_columns("product")
    }

    # Add cost_price if missing
    if "cost_price" not in product_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    """
                    ALTER TABLE product
                    ADD COLUMN cost_price FLOAT DEFAULT 0
                    """
                )
            )

    # Add sale_price if missing
    if "sale_price" not in product_columns:

        with db.engine.begin() as connection:

            connection.execute(
                text(
                    """
                    ALTER TABLE product
                    ADD COLUMN sale_price FLOAT
                    """
                )
            )

# ==========================================
# Flask Login
# ==========================================

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"

login_manager.login_message = "Please log in first."


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(
        int(user_id)
    )


# ==========================================
# Print Database
# ==========================================

print(
    "📁 Using database:",
    app.config["SQLALCHEMY_DATABASE_URI"]
)


# ==========================================
# Import Routes
# ==========================================

from routes import *


# ==========================================
# Run App
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
