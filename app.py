from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from dotenv import load_dotenv
import os
from flask_mail import Mail

# تحميل ملف .env
load_dotenv()

# إنشاء التطبيق
app = Flask(__name__)
app.config.from_object(Config)

# 🔹 إعداد القيم الأساسية
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'supersecretkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔹 إعداد البريد (محلي فقط)
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 8028
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@crochetrory.com'

# 🔹 تهيئة البريد
mail = Mail(app)

# ✅ تأكيد قاعدة البيانات المستخدمة
print("📁 Using database file:", app.config['SQLALCHEMY_DATABASE_URI'])

# 🟢 استيراد قاعدة البيانات من models
from models import db, Product, Order, OrderItem, User

# 🟢 تهيئة قاعدة البيانات مع التطبيق
db.init_app(app)
migrate = Migrate(app, db)

# 🟢 استيراد المسارات بعد تهيئة قاعدة البيانات
from routes import *

# 🟢 تشغيل التطبيق
if __name__ == "__main__":
    app.run(debug=True)


from models import Message, Product, User, Cart, Order, OrderItem  # <-- تأكدي إن Message هنا

with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully!")
