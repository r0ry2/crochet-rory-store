from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import (
    FileField,
    FloatField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField
)
from wtforms.validators import DataRequired


db = SQLAlchemy()


# ==================================================
# 📝 FORMS
# ==================================================
class AddProductForm(FlaskForm):
    name = StringField(
        "Product Name",
        validators=[DataRequired()]
    )

    price = FloatField(
        "Price",
        validators=[DataRequired()]
    )

    description = TextAreaField(
        "Description",
        validators=[DataRequired()]
    )

    image = FileField(
        "Product Image",
        validators=[
            FileAllowed(
                ["jpg", "png", "jpeg"],
                "Images only!"
            )
        ]
    )

    publish_location = SelectField(
        "Publish Product",
        choices=[
            ("both", "Show in Home + Products pages"),
            ("products_only", "Show only in Products page"),
            ("home_only", "Show only in Home page")
        ],
        default="products_only"
    )

    submit = SubmitField("Save")


# ==================================================
# 🧸 PRODUCT
# ==================================================
class Product(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    price = db.Column(
        db.Float,
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    image = db.Column(
        db.String(200)
    )

    # ==========================
    # Product Category
    # ==========================

    category = db.Column(
        db.String(100),
        default="Dolls"
    )

    # ==========================
    # Stock Quantity
    # ==========================

    stock = db.Column(
        db.Integer,
        default=1
    )

    # ==========================
    # New Product Badge
    # ==========================

    is_new = db.Column(
        db.Boolean,
        default=True
    )

    # ==========================
    # Publish Location
    # ==========================

    publish_location = db.Column(
        db.String(20),
        default="products_only"
    )

    def __repr__(self):
        return f"<Product {self.name}>"
# ==================================================
# 👤 USER
# ==================================================
class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(200),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="user"
    )

    confirmed = db.Column(
        db.Boolean,
        default=False
    )
    verification_code = db.Column(
        db.String(6),
        nullable=True
    )

    verification_expiry = db.Column(
        db.DateTime,
        nullable=True
    )
    # ==========================
    # Personal Information
    # ==========================

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    birthday = db.Column(
        db.String(20),
        nullable=True
    )

    gender = db.Column(
        db.String(20),
        nullable=True
    )

    nationality = db.Column(
        db.String(50),
        nullable=True
    )

    profile_image = db.Column(
        db.String(255),
        default="default.png"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )  


# ==================================================
# 🛒 CART
# ==================================================
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        default=1
    )

    user = db.relationship(
        "User",
        backref="cart_items",
        lazy=True
    )

    product = db.relationship(
        "Product",
        lazy=True
    )

    def __repr__(self):
        return f"<Cart {self.user_id} - {self.product_id}>"

# ==================================================
# ❤️ WISHLIST
# ==================================================
class Wishlist(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    user = db.relationship(
        "User",
        backref="wishlist_items",
        lazy=True
    )

    product = db.relationship(
        "Product",
        lazy=True
    )

    def __repr__(self):
        return f"<Wishlist {self.user_id} - {self.product_id}>"
# ==================================================
# 📦 ORDER
# ==================================================
class Order(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    customer_name = db.Column(
        db.String(100)
    )

    customer_email = db.Column(
        db.String(120)
    )

    address = db.Column(
        db.String(255)
    )

    payment_method = db.Column(
        db.String(50)
    )

    total = db.Column(
        db.Float
    )

    # حالات الطلب:
    # Pending Payment
    # Pending Review
    # Processing
    # Shipping
    # Delivered
    # Cancelled
    status = db.Column(
        db.String(50),
        default="Pending Payment"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # (اختياري) يضاف لاحقًا عند الشحن
    tracking_number = db.Column(
        db.String(100)
    )

    shipping_company = db.Column(
        db.String(100)
    )

    user = db.relationship(
        "User",
        backref="orders",
        lazy=True
    )

    def __repr__(self):
        return f"<Order {self.id} - {self.customer_name}>"
class Notification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    message = db.Column(
        db.String(255)
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
# ==================================================
# 👀 VISITORS
# ==================================================
class Visitor(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    ip_address = db.Column(
        db.String(100)
    )

    page = db.Column(
        db.String(255)
    )

    visited_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
# ==================================================
# 🧾 ORDER ITEM
# ==================================================
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id")
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id")
    )

    quantity = db.Column(
        db.Integer,
        default=1
    )

    price = db.Column(db.Float)

    order = db.relationship(
        "Order",
        backref="items",
        lazy=True
    )

    product = db.relationship(
        "Product",
        lazy=True
    )

    def __repr__(self):
        return (
            f"<OrderItem order={self.order_id}, "
            f"product={self.product_id}>"
        )


# ==================================================
# 💌 CONTACT MESSAGES
# ==================================================
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )


# ==================================================
# ⭐ REVIEWS
# ==================================================
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    stars = db.Column(
        db.Integer,
        nullable=False,
        default=5
    )

    admin_reply = db.Column(db.Text)