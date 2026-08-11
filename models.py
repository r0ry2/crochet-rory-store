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

    # ==========================
    # Product Name
    # ==========================

    name = db.Column(
        db.String(100),
        nullable=False
    )

    # ==========================
    # Product Price
    # السعر الأساسي / الحقيقي
    # ==========================

    price = db.Column(
        db.Float,
        nullable=False
    )

    # ==========================
    # 💰 Cost Price
    # سعر التكلفة
    # ==========================

    cost_price = db.Column(
        db.Float,
        nullable=True,
        default=0
    )

    # ==========================
    # 🏷️ Sale Price
    # سعر الخصم / التخفيض
    # ==========================

    sale_price = db.Column(
        db.Float,
        nullable=True,
        default=None
    )

    # ==========================
    # Product Description
    # ==========================

    description = db.Column(
        db.Text,
        nullable=False
    )

    # ==========================
    # Product Image
    # ==========================

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
    # ✨ Customization
    # هل المنتج قابل للتخصيص؟
    # ==========================

    is_customizable = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # ==========================
    # Publish Location
    # ==========================

    publish_location = db.Column(
        db.String(20),
        default="products_only"
    )

    # ==========================
    # Purchase Count
    # عدد مرات شراء المنتج
    # ==========================

    purchase_count = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    # ==========================
    # Created At
    # تاريخ إضافة المنتج
    # ==========================

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ==================================================
    # 📊 SALE STATUS
    # ==================================================

    @property
    def has_discount(self):

        return (
            self.sale_price is not None
            and self.sale_price > 0
            and self.sale_price < self.price
        )

    # ==================================================
    # 💵 CURRENT PRICE
    # السعر الذي سيدفعه العميل
    # ==================================================

    @property
    def current_price(self):

        if self.has_discount:

            return self.sale_price

        return self.price

    # ==================================================
    # 💰 PROFIT
    # الربح من بيع قطعة واحدة
    # ==================================================

    @property
    def profit(self):

        if self.cost_price is None:

            return 0

        return self.current_price - self.cost_price

    # ==================================================
    # 📉 DISCOUNT AMOUNT
    # قيمة الخصم
    # ==================================================

    @property
    def discount_amount(self):

        if not self.has_discount:

            return 0

        return self.price - self.sale_price

    # ==================================================
    # 📉 DISCOUNT PERCENTAGE
    # نسبة الخصم
    # ==================================================

    @property
    def discount_percentage(self):

        if not self.has_discount or self.price <= 0:

            return 0

        return round(
            ((self.price - self.sale_price) / self.price) * 100,
            2
        )

    # ==========================
    # Representation
    # ==========================

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

    # ==========================
    # 👤 CUSTOMER
    # ==========================

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )

    customer_name = db.Column(
        db.String(100),
        nullable=False
    )

    customer_email = db.Column(
        db.String(120),
        nullable=True
    )

    customer_phone = db.Column(
        db.String(30),
        nullable=True
    )

    # ==========================
    # 📍 DELIVERY ADDRESS
    # ==========================

    address = db.Column(
        db.String(255),
        nullable=True
    )

    city = db.Column(
        db.String(100),
        nullable=True
    )

    district = db.Column(
        db.String(100),
        nullable=True
    )

    postal_code = db.Column(
        db.String(20),
        nullable=True
    )

    # ==========================
    # 💳 PAYMENT
    # ==========================

    payment_method = db.Column(
        db.String(50),
        nullable=True
    )

    # ==========================
    # 🛍️ PRICES
    # ==========================

    # مجموع أسعار المنتجات
    products_total = db.Column(
        db.Float,
        default=0
    )

    # مجموع الإضافات
    extras_total = db.Column(
        db.Float,
        default=0
    )

    # سعر الشحن
    shipping_cost = db.Column(
        db.Float,
        default=0
    )

    # الخصم
    discount = db.Column(
        db.Float,
        default=0
    )

    # الكوبون المستخدم
    coupon_code = db.Column(
        db.String(50),
        nullable=True
    )

    # الإجمالي النهائي
    total = db.Column(
        db.Float,
        default=0
    )

    # ==========================
    # 🚚 SHIPPING
    # ==========================

    shipping_method = db.Column(
        db.String(100),
        nullable=True
    )

    shipping_company = db.Column(
        db.String(100),
        nullable=True
    )

    tracking_number = db.Column(
        db.String(100),
        nullable=True
    )

    # ==========================
    # 📅 DELIVERY
    # ==========================

    # الموعد المتوقع للتسليم
    estimated_delivery = db.Column(
        db.DateTime,
        nullable=True
    )

    # تاريخ التسليم الفعلي
    delivered_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # ==========================
    # 📦 ORDER STATUS
    # ==========================

    # الحالات:
    #
    # Pending Payment
    # Pending Review
    # Processing
    # Completed
    # Shipping
    # Delivered
    # Cancelled

    status = db.Column(
        db.String(50),
        default="Pending Payment"
    )

    # ==========================
    # 🕐 DATES
    # ==========================

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ==========================
    # 🔗 RELATIONSHIP
    # ==========================

    user = db.relationship(
        "User",
        backref="orders",
        lazy=True
    )

    # ==========================
    # 💰 CALCULATE TOTAL
    # ==========================

    def calculate_total(self):

        products = self.products_total or 0
        extras = self.extras_total or 0
        shipping = self.shipping_cost or 0
        discount = self.discount or 0

        self.total = (
            products
            + extras
            + shipping
            - discount
        )

        return self.total

    # ==========================
    # 📌 REPRESENTATION
    # ==========================

    def __repr__(self):

        return (
            f"<Order "
            f"{self.id} - "
            f"{self.customer_name} - "
            f"{self.status}>"
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
# 🔔 NOTIFICATIONS
# ==================================================

class Notification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Notification {self.id}>"
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
# 🚚 SHIPPING METHOD
# ==================================================

class ShippingMethod(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name_ar = db.Column(
        db.String(100),
        nullable=False
    )

    name_en = db.Column(
        db.String(100),
        nullable=False
    )

    price = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    min_days = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    max_days = db.Column(
        db.Integer,
        nullable=False,
        default=3
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<ShippingMethod {self.name_en}>"
# ==================================================
# 🎟️ COUPON
# ==================================================

class Coupon(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # كود الكوبون
    code = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    # نوع الخصم:
    # percentage = نسبة مئوية
    # fixed = مبلغ ثابت
    discount_type = db.Column(
        db.String(20),
        nullable=False,
        default="percentage"
    )

    # قيمة الخصم
    discount_value = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    # الحد الأدنى لقيمة الطلب
    minimum_order = db.Column(
        db.Float,
        default=0
    )

    # الحد الأقصى لقيمة الخصم
    # يستخدم مع الخصم بالنسبة المئوية
    maximum_discount = db.Column(
        db.Float,
        nullable=True
    )

    # تاريخ بداية الكوبون
    start_date = db.Column(
        db.DateTime,
        nullable=True
    )

    # تاريخ انتهاء الكوبون
    expiry_date = db.Column(
        db.DateTime,
        nullable=True
    )

    # عدد مرات الاستخدام المسموح بها
    usage_limit = db.Column(
        db.Integer,
        nullable=True
    )

    # عدد مرات الاستخدام الحالية
    used_count = db.Column(
        db.Integer,
        default=0
    )

    # حالة الكوبون
    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # ==================================================
    # CHECK VALIDITY
    # ==================================================

    def is_valid(self, order_amount=0):

        now = datetime.utcnow()

        # الكوبون غير مفعل
        if not self.is_active:
            return False

        # الحد الأدنى للطلب
        if order_amount < (self.minimum_order or 0):
            return False

        # تاريخ البداية
        if self.start_date and now < self.start_date:
            return False

        # تاريخ الانتهاء
        if self.expiry_date and now > self.expiry_date:
            return False

        # حد الاستخدام
        if (
            self.usage_limit is not None
            and self.used_count >= self.usage_limit
        ):
            return False

        return True

    # ==================================================
    # CALCULATE DISCOUNT
    # ==================================================

    def calculate_discount(self, order_amount):

        if not self.is_valid(order_amount):
            return 0

        # نسبة مئوية
        if self.discount_type == "percentage":

            discount = (
                order_amount
                * self.discount_value
                / 100
            )

            # الحد الأقصى للخصم
            if self.maximum_discount is not None:

                discount = min(
                    discount,
                    self.maximum_discount
                )

        # مبلغ ثابت
        elif self.discount_type == "fixed":

            discount = self.discount_value

        else:

            discount = 0

        # لا يمكن أن يكون الخصم أكبر من قيمة الطلب
        discount = min(
            discount,
            order_amount
        )

        return round(discount, 2)

    def __repr__(self):

        return f"<Coupon {self.code}>"
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