import os
import uuid

from datetime import datetime, timedelta

from dotenv import load_dotenv

from flask import (
    Flask,
    session,
    request
)

from flask_mail import Mail

from flask_login import (
    LoginManager,
    current_user
)

from flask_migrate import Migrate

from flask_babel import Babel

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
    Notification,
    Visitor,
    Advertisement
)


# ==================================================
# 🔎 DEBUG - CHECK LOADED PRODUCT MODEL
# ==================================================

print("🔥 MODELS FILE:", Product.__module__)

print("🔥 PRODUCT COLUMNS:")

print(
    Product.__table__.columns.keys()
)


# ==================================================
# 🔎 DEBUG - CHECK VISITOR MODEL
# ==================================================

print("🔥 VISITOR COLUMNS:")

print(
    Visitor.__table__.columns.keys()
)


# ==================================================
# Load Environment Variables
# ==================================================

load_dotenv()


# ==================================================
# Create Flask App
# ==================================================

app = Flask(__name__)

app.config.from_object(Config)


# ==================================================
# 🌐 Babel
# ==================================================

app.config["BABEL_DEFAULT_LOCALE"] = "en"

app.config["BABEL_SUPPORTED_LOCALES"] = [
    "en",
    "ar"
]


def get_locale():

    return session.get(
        "language",
        "en"
    )


babel = Babel(
    app,
    locale_selector=get_locale
)


# ==================================================
# Context Processor
# ==================================================

@app.context_processor
def inject_locale():

    return {
        "current_lang":
            session.get(
                "language",
                "en"
            )
    }


# ==================================================
# 🔐 Secret Key
# ==================================================

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "supersecretkey"
)


# ==================================================
# 🗄️ Database Configuration
# ==================================================

database_url = os.getenv(
    "DATABASE_URL"
)


if database_url:

    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = database_url

else:

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "sqlite:///data.sqlite"


app.config[
    "SQLALCHEMY_TRACK_MODIFICATIONS"
] = False


# ==================================================
# 📧 Mail
# ==================================================

mail = Mail(app)


# ==================================================
# 🗄️ Initialize Database
# ==================================================

db.init_app(app)


migrate = Migrate(
    app,
    db
)


# ==================================================
# 🔧 Update Existing Product Table
# ==================================================

with app.app_context():

    from sqlalchemy import (
        inspect,
        text
    )

    # ----------------------------------------------
    # Create missing tables
    # ----------------------------------------------

    db.create_all()


    # ----------------------------------------------
    # Inspect Product table
    # ----------------------------------------------

    inspector = inspect(
        db.engine
    )


    product_columns = {
        column["name"]
        for column in inspector.get_columns(
            "product"
        )
    }


    print(
        "🔎 PRODUCT DATABASE COLUMNS:",
        sorted(product_columns)
    )


    # ==================================================
    # Add is_customizable
    # ==================================================

    if "is_customizable" not in product_columns:

        try:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        """
                        ALTER TABLE product
                        ADD COLUMN is_customizable
                        BOOLEAN NOT NULL DEFAULT FALSE
                        """
                    )
                )

            print(
                "✅ Added is_customizable column"
            )

        except Exception as e:

            print(
                "⚠️ Could not add is_customizable:",
                e
            )


    # ==================================================
    # Add purchase_count
    # ==================================================

    if "purchase_count" not in product_columns:

        try:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        """
                        ALTER TABLE product
                        ADD COLUMN purchase_count
                        INTEGER NOT NULL DEFAULT 0
                        """
                    )
                )

            print(
                "✅ Added purchase_count column"
            )

        except Exception as e:

            print(
                "⚠️ Could not add purchase_count:",
                e
            )


    # ==================================================
    # Add created_at
    # ==================================================

    if "created_at" not in product_columns:

        try:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        """
                        ALTER TABLE product
                        ADD COLUMN created_at
                        TIMESTAMP
                        """
                    )
                )

            print(
                "✅ Added created_at column"
            )

        except Exception as e:

            print(
                "⚠️ Could not add created_at:",
                e
            )


    # ==================================================
    # Add cost_price
    # ==================================================

    if "cost_price" not in product_columns:

        try:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        """
                        ALTER TABLE product
                        ADD COLUMN cost_price
                        FLOAT DEFAULT 0
                        """
                    )
                )

            print(
                "✅ Added cost_price column"
            )

        except Exception as e:

            print(
                "⚠️ Could not add cost_price:",
                e
            )


    # ==================================================
    # Add sale_price
    # ==================================================

    if "sale_price" not in product_columns:

        try:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        """
                        ALTER TABLE product
                        ADD COLUMN sale_price
                        FLOAT
                        """
                    )
                )

            print(
                "✅ Added sale_price column"
            )

        except Exception as e:

            print(
                "⚠️ Could not add sale_price:",
                e
            )


    # ==================================================
    # Re-check Product Columns
    # ==================================================

    inspector = inspect(
        db.engine
    )


    final_product_columns = {
        column["name"]
        for column in inspector.get_columns(
            "product"
        )
    }


    print(
        "✅ FINAL PRODUCT DATABASE COLUMNS:",
        sorted(final_product_columns)
    )


# ==================================================
# 🔑 Flask Login
# ==================================================

login_manager = LoginManager()

login_manager.init_app(
    app
)


login_manager.login_view = "login"


login_manager.login_message = (
    "Please log in first."
)


@login_manager.user_loader
def load_user(user_id):

    return User.query.get(
        int(user_id)
    )


# ==================================================
# 👀 VISITOR TRACKING SYSTEM
# ==================================================

# مدة الزيارة الواحدة
VISITOR_TIMEOUT = timedelta(
    minutes=30
)


@app.before_request
def track_visitor():

    # ==================================================
    # تجاهل ملفات static
    # ==================================================

    if request.endpoint == "static":

        return


    # ==================================================
    # الوقت الحالي
    # ==================================================

    now = datetime.utcnow()


    # ==================================================
    # إنشاء Visitor ID للزائر
    # ==================================================

    if "visitor_id" not in session:

        session["visitor_id"] = str(
            uuid.uuid4()
        )


    visitor_id = session[
        "visitor_id"
    ]


    # ==================================================
    # تحديد نوع الزائر
    # ==================================================

    if current_user.is_authenticated:

        visitor_type = "registered"

        user_id = current_user.id

    else:

        visitor_type = "guest"

        user_id = None


    # ==================================================
    # 🔎 البحث عن آخر زيارة لهذا المتصفح
    # ==================================================

    visitor = (
        Visitor.query
        .filter_by(
            visitor_id=visitor_id
        )
        .order_by(
            Visitor.last_activity.desc()
        )
        .first()
    )


    # ==================================================
    # 👤 إذا عنده زيارة سابقة
    # ==================================================

    if visitor:

        time_since_last_activity = (
            now - visitor.last_activity
        )


        # ==================================================
        # ⏰ مر 30 دقيقة أو أكثر
        # → زيارة جديدة
        # ==================================================

        if (
            time_since_last_activity
            >= VISITOR_TIMEOUT
        ):

            new_visitor = Visitor(

                visitor_id=visitor_id,

                user_id=user_id,

                visitor_type=visitor_type,

                started_at=now,

                last_activity=now,

                visited_at=now,

                ip_address=request.remote_addr,

                page=request.path
            )


            db.session.add(
                new_visitor
            )


            print(
                "🆕 NEW VISIT:",
                visitor_id
            )


        # ==================================================
        # 🔄 أقل من 30 دقيقة
        # → نفس الزيارة
        # ==================================================

        else:

            visitor.last_activity = now

            visitor.page = request.path

            visitor.user_id = user_id

            visitor.visitor_type = visitor_type

            visitor.ip_address = (
                request.remote_addr
            )


            print(
                "🔄 SAME VISIT:",
                visitor_id
            )


    # ==================================================
    # 🆕 أول زيارة لهذا المتصفح
    # ==================================================

    else:

        new_visitor = Visitor(

            visitor_id=visitor_id,

            user_id=user_id,

            visitor_type=visitor_type,

            started_at=now,

            last_activity=now,

            visited_at=now,

            ip_address=request.remote_addr,

            page=request.path
        )


        db.session.add(
            new_visitor
        )


        print(
            "🆕 FIRST VISIT:",
            visitor_id
        )


    # ==================================================
    # 💾 حفظ التغييرات
    # ==================================================

    try:

        db.session.commit()

    except Exception as e:

        print(
            "❌ Visitor tracking error:",
            e
        )

        db.session.rollback()


# ==================================================
# 📁 Print Database
# ==================================================

print(
    "📁 Using database:",
    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ]
)


# ==================================================
# Import Routes
# ==================================================

from routes import *


# ==================================================
# Run App
# ==================================================

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