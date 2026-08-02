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
    Wishlist
)

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

babel = Babel(app, locale_selector=get_locale)

@app.context_processor
def inject_locale():
    return {
        "current_lang": session.get("language", "en")
    }

# ==========================================
# Secret Key & Database
# ==========================================
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecretkey")

database_url = os.getenv("DATABASE_URL")

if database_url:
    database_url = database_url.replace("postgres://", "postgresql://", 1)
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
migrate = Migrate(app, db)

# ==========================================
# Flask Login
# ==========================================
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"
login_manager.login_message = "Please log in first."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==========================================
# Print Database
# ==========================================
print("📁 Using database:", app.config["SQLALCHEMY_DATABASE_URI"])

# ==========================================
# Import Routes
# ==========================================
from routes import *



# ==========================================
# Run App
# ==========================================
if __name__ == "__main__":
    app.run(debug=True)