from flask import (
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
    
)
import json
import re
import secrets
from datetime import datetime, timedelta

from app import app, db, mail

import resend
import os
from models import (
    Product,
    Order,
    OrderItem,
    User,
    Cart,
    Message,
    Review,
    Wishlist,
    AddProductForm,
    db,
    Notification,
    Visitor,
    ShippingMethod,
    Coupon,
    Advertisement,
    Visitor


)
import uuid
from forms import (
    LoginForm,
    RegisterForm,
    ProductForm,
    VerifyCodeForm
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user
)

# ==================================================
# 📧 RESEND
# ==================================================

resend.api_key = os.environ.get("RESEND_API_KEY")

from werkzeug.utils import secure_filename

from datetime import datetime
import os

from datetime import datetime
from flask import jsonify
from sqlalchemy import func
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message as MailMessage
# ==================================================
# 📧 TEST RESEND EMAIL
# ==================================================

@app.route("/test-resend")
def test_resend():

    try:

        params = {
            "from": "onboarding@resend.dev",
            "to": ["noni200217noni@gmail.com"],
            "subject": "Crochet Rory Store - Test Email",
            "html": """
                <h2>💕 Crochet Rory Store</h2>

                <p>
                    هذا إيميل تجريبي من متجر روري للكروشيه.
                </p>

                <p>
                    إذا وصلتك هذه الرسالة، فهذا يعني أن
                    Resend API يعمل بشكل صحيح مع Railway.
                </p>

                <p>
                    ✅ Resend is working!
                </p>
            """
        }

        email = resend.Emails.send(params)

        print("✅ RESEND EMAIL SENT:", email)

        return "RESEND EMAIL SENT SUCCESSFULLY ✅"

    except Exception as e:

        print("❌ RESEND ERROR:", e)

        return f"RESEND ERROR: {e}", 500

@app.route("/language/<lang>")
def change_language(lang):

    if lang in ["en", "ar"]:
        session["language"] = lang

    return redirect(request.referrer or url_for("index"))
# ==========================================
# 📂 Upload Settings
# ==========================================

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ==========================================
# 🔐 Email Confirmation Serializer
# ==========================================

# ==========================================
# 🛒 CART HELPERS
# ==========================================

def session_get_cart():
    """Return guest cart stored in session."""
    return session.get("cart", [])


def session_save_cart(cart):
    session["cart"] = cart
    session.modified = True


def get_db_cart_items(user_id):
    """Return user's cart stored in database."""
    return Cart.query.filter_by(user_id=user_id).all()


def cart_items_to_json(cart_items):
    """Convert database cart items into JSON."""

    data = []

    for item in cart_items:
        product = Product.query.get(item.product_id)

        if not product:
            continue

        data.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": item.quantity,
            "image": url_for(
                "static",
                filename=f"uploads/products/{product.image}"
            ) if product.image else ""
        })

    return data


def merge_session_cart_into_db(user_id):
    """
    Merge guest session cart into database after login.
    """

    session_cart = session_get_cart()

    if not session_cart:
        return

    for item in session_cart:

        product_id = item.get("product_id")
        quantity = int(item.get("quantity", 1))

        if not product_id:
            continue

        existing = Cart.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()

        if existing:
            existing.quantity += quantity
        else:
            db.session.add(
                Cart(
                    user_id=user_id,
                    product_id=product_id,
                    quantity=quantity
                )
            )

    db.session.commit()
    session_save_cart([])


# ==========================================
# 🔍 SEARCH
# ==========================================
@app.route("/search")
def search():

    query = request.args.get("q", "").strip()

    # إذا المستخدم بحث عن كلمة
    if query:

        products = Product.query.filter(
            Product.name.ilike(f"%{query}%")
        ).all()

    # إذا فتح البحث بدون كلمة
    else:

        products = Product.query.all()

    return render_template(
        "products.html",
        products=products,
        query=query
    )

# ==================================================
# ✏️ EDIT PRODUCT
# ==================================================

@app.route("/admin/edit_product/<int:id>", methods=["POST"])
@login_required
def edit_product(id):

    # ==================================================
    # 🌐 CURRENT LANGUAGE
    # ==================================================

    current_lang = session.get(
        "lang",
        session.get("language", "ar")
    )

    # ==================================================
    # 🔐 ADMIN CHECK
    # ==================================================

    if current_user.role != "admin":
        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )

        return redirect(
            url_for("home_logged")
        )

    # ==================================================
    # 📦 GET PRODUCT
    # ==================================================

    product = Product.query.get_or_404(id)

    # ==================================================
    # 📝 GET FORM
    # ==================================================

    form = ProductForm()

    # ==================================================
    # 🖼️ IMAGE
    # ==================================================

    filename = product.image

    if form.image.data:

        image_file = form.image.data

        if image_file.filename:

            filename = secure_filename(
                image_file.filename
            )

            image_path = os.path.join(
                app.root_path,
                "static",
                "images",
                filename
            )

            image_file.save(
                image_path
            )

    # ==================================================
    # 📦 QUANTITY
    # ==================================================

    quantity = request.form.get(
        "quantity",
        product.stock
    )

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = product.stock

    # منع الكمية السالبة
    if quantity < 0:
        quantity = 0

    # ==================================================
    # 💰 COST PRICE
    # ==================================================

    cost_price = request.form.get(
        "cost_price",
        product.cost_price
    )

    try:
        cost_price = float(cost_price)
    except (TypeError, ValueError):
        cost_price = product.cost_price or 0

    # منع القيمة السالبة
    if cost_price < 0:
        cost_price = 0

    # ==================================================
    # 🏷️ SALE PRICE
    # ==================================================

    sale_price = request.form.get(
        "sale_price",
        None
    )

    # إذا ترك المستخدم السعر المخفض فارغًا
    if sale_price in [None, ""]:
        sale_price = None

    else:

        try:
            sale_price = float(
                sale_price
            )

        except (TypeError, ValueError):
            sale_price = None

    # منع السعر المخفض من أن يكون سالبًا
    if (
        sale_price is not None
        and sale_price < 0
    ):
        sale_price = None

    # ==================================================
    # ⚠️ CHECK SALE PRICE
    # ==================================================

    # السعر المخفض لا يكون أعلى من السعر الأصلي

    if sale_price is not None:

        if sale_price >= form.price.data:
            sale_price = None

    # ==================================================
    # 📏 SIZE PRICES
    # ==================================================
    # قراءة أسعار الأحجام من نموذج التعديل
    #
    # مثال:
    # Small  = 50
    # Medium = 70
    # Large  = 90
    # ==================================================

    size_prices = {}

    size_names = request.form.getlist(
        "size_name[]"
    )

    size_values = request.form.getlist(
        "size_price[]"
    )

    for index, size_name in enumerate(size_names):

        size_name = size_name.strip()

        if not size_name:
            continue

        price_value = ""

        if index < len(size_values):
            price_value = size_values[index]

        try:
            price_value = float(
                price_value
            )

        except (TypeError, ValueError):
            continue

        # منع السعر السالب
        if price_value < 0:
            continue

        size_prices[size_name] = price_value

    # ==================================================
    # ✏️ UPDATE PRODUCT
    # ==================================================

    product.name = form.name.data

    # السعر الأصلي
    product.price = form.price.data

    # سعر التكلفة
    product.cost_price = cost_price

    # السعر المخفض
    product.sale_price = sale_price

    # الوصف
    product.description = form.description.data

    # الصورة
    product.image = filename

    # مكان العرض
    product.publish_location = (
        form.publish_location.data
    )

    # التخصيص
    product.is_customizable = (
        form.is_customizable.data
    )

    # الكمية
    product.stock = quantity

    # ==================================================
    # 📏 UPDATE SIZE PRICES
    # ==================================================

    product.size_prices = size_prices

    # ==================================================
    # 💾 SAVE CHANGES
    # ==================================================

    db.session.commit()

    # ==================================================
    # ✅ SUCCESS MESSAGE
    # ==================================================

    flash(
        (
            "✅ تم تعديل المنتج بنجاح!"
            if current_lang == "ar"
            else "✅ Product updated successfully!"
        ),
        "success"
    )

    # ==================================================
    # ↩️ BACK TO PRODUCTS
    # ==================================================

    return redirect(
        url_for("admin_products")
    )

# ==================================================
# 🗑️ DELETE PRODUCT
# ==================================================

@app.route("/admin/delete_product/<int:id>", methods=["POST"])
@login_required
def delete_product(id):

    # ==================================================
    # 🔐 ADMIN CHECK
    # ==================================================

    if current_user.role != "admin":
        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )
        return redirect(url_for("home_logged"))

    # ==================================================
    # 🌐 CURRENT LANGUAGE
    # ==================================================

    current_lang = session.get("lang", "ar")

    try:

        # ==================================================
        # 📦 FIND PRODUCT
        # ==================================================

        product = Product.query.get_or_404(id)

        # ==================================================
        # 🛒 REMOVE FROM CART
        # ==================================================

        Cart.query.filter_by(
            product_id=product.id
        ).delete(
            synchronize_session=False
        )

        # ==================================================
        # ❤️ REMOVE FROM WISHLIST
        # ==================================================

        Wishlist.query.filter_by(
            product_id=product.id
        ).delete(
            synchronize_session=False
        )

        # ==================================================
        # 📦 REMOVE FROM ORDER ITEMS
        # ==================================================

        OrderItem.query.filter_by(
            product_id=product.id
        ).delete(
            synchronize_session=False
        )

        # ==================================================
        # 🗑️ DELETE PRODUCT
        # ==================================================

        db.session.delete(product)
        db.session.commit()

        # ==================================================
        # ✅ SUCCESS
        # ==================================================

        if current_lang == "ar":
            flash(
                "🗑️ تم حذف المنتج بنجاح!",
                "success"
            )
        else:
            flash(
                "🗑️ Product deleted successfully!",
                "success"
            )

    except Exception as e:

        # ==================================================
        # 🔄 ROLLBACK
        # ==================================================

        db.session.rollback()

        print("❌ DELETE PRODUCT ERROR:", e)

        # ==================================================
        # ❌ ERROR
        # ==================================================

        if current_lang == "ar":
            flash(
                "❌ حدث خطأ أثناء حذف المنتج.",
                "danger"
            )
        else:
            flash(
                "❌ Error deleting product.",
                "danger"
            )

    # ==================================================
    # 🔙 RETURN TO PRODUCTS
    # ==================================================

    return redirect(url_for("admin_products"))

# ==================================================
# ➕ ADD PRODUCT
# ==================================================

# ==================================================
# ➕ ADD PRODUCT
# ==================================================

@app.route("/admin/add_product", methods=["GET", "POST"])
@login_required
def add_product():

    # ==================================================
    # 🔐 ADMIN CHECK
    # ==================================================

    if current_user.role != "admin":
        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )
        return redirect(
            url_for("home_logged")
        )

    # ==================================================
    # 🌐 LANGUAGE
    # ==================================================

    current_lang = session.get(
        "language",
        "ar"
    )

    # ==================================================
    # 📝 PRODUCT FORM
    # ==================================================

    form = ProductForm()

    # ==================================================
    # 📦 GET EXISTING PRODUCTS
    # ==================================================

    products = Product.query.order_by(
        Product.id.desc()
    ).all()

    # ==================================================
    # ✅ FORM SUBMITTED
    # ==================================================

    if form.validate_on_submit():

        # ==================================================
        # 🖼️ IMAGE
        # ==================================================

        filename = None

        if form.image.data:

            image_file = form.image.data

            if image_file.filename:

                filename = secure_filename(
                    image_file.filename
                )

                # ==================================================
                # 📁 CREATE UPLOADS FOLDER
                # ==================================================

                upload_folder = os.path.join(
                    app.root_path,
                    "static",
                    "uploads",
                    "products"
                )

                os.makedirs(
                    upload_folder,
                    exist_ok=True
                )

                # ==================================================
                # 📍 IMAGE PATH
                # ==================================================

                image_path = os.path.join(
                    upload_folder,
                    filename
                )

                # ==================================================
                # 💾 SAVE IMAGE TO VOLUME
                # ==================================================

                image_file.save(
                    image_path
                )

        # ==================================================
        # 📦 PRODUCT QUANTITY
        # ==================================================

        quantity = request.form.get(
            "quantity",
            1
        )

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1

        # منع الكمية من أن تكون سالبة
        if quantity < 0:
            quantity = 0

        # ==================================================
        # 💰 COST PRICE
        # ==================================================

        cost_price = request.form.get(
            "cost_price",
            ""
        )

        try:
            cost_price = float(
                cost_price
            )
        except (TypeError, ValueError):
            cost_price = 0

        # منع سعر التكلفة من أن يكون سالبًا
        if cost_price < 0:
            cost_price = 0

        # ==================================================
        # 🏷️ SALE PRICE
        # ==================================================

        sale_price = request.form.get(
            "sale_price",
            ""
        )

        try:
            sale_price = float(
                sale_price
            )
        except (TypeError, ValueError):
            sale_price = None

        # ==================================================
        # 🧹 CLEAN SALE PRICE
        # ==================================================

        if sale_price is not None:

            # منع السعر المخفض من أن يكون سالبًا
            if sale_price < 0:

                sale_price = None

            # إذا كان السعر المخفض أكبر أو يساوي السعر الأصلي
            elif sale_price >= form.price.data:

                sale_price = None

        # ==================================================
        # 📏 SIZE PRICES
        # ==================================================

        size_prices = {}

        size_names = request.form.getlist(
            "size_name[]"
        )

        size_values = request.form.getlist(
            "size_price[]"
        )

        for index, size_name in enumerate(
            size_names
        ):

            size_name = size_name.strip()

            if not size_name:
                continue

            price_value = ""

            if index < len(size_values):
                price_value = size_values[index]

            try:
                price_value = float(
                    price_value
                )
            except (TypeError, ValueError):
                continue

            # منع السعر من أن يكون سالبًا
            if price_value < 0:
                continue

            size_prices[size_name] = price_value

        # ==================================================
        # 🧸 CREATE PRODUCT
        # ==================================================

        product = Product(

            # ----------------------------------------------
            # Product Information
            # ----------------------------------------------

            name=form.name.data,

            price=form.price.data,

            description=form.description.data,

            # ----------------------------------------------
            # 📏 Size Prices
            # ----------------------------------------------

            size_prices=size_prices,

            # ----------------------------------------------
            # 💰 Cost Price
            # ----------------------------------------------

            cost_price=cost_price,

            # ----------------------------------------------
            # 🏷️ Sale Price
            # ----------------------------------------------

            sale_price=sale_price,

            # ----------------------------------------------
            # Product Image
            # ----------------------------------------------

            image=filename,

            # ----------------------------------------------
            # Publish Location
            # ----------------------------------------------

            publish_location=form.publish_location.data,

            # ----------------------------------------------
            # ✨ Customization
            # ----------------------------------------------

            is_customizable=form.is_customizable.data,

            # ----------------------------------------------
            # 📦 Stock / Quantity
            # ----------------------------------------------

            stock=quantity,

            # ----------------------------------------------
            # 🆕 New Product
            # ----------------------------------------------

            is_new=True,

            # ----------------------------------------------
            # 🛒 Purchase Count
            # ----------------------------------------------

            purchase_count=0
        )

        # ==================================================
        # 💾 SAVE PRODUCT
        # ==================================================

        db.session.add(product)

        db.session.commit()

        # ==================================================
        # 🔄 REFRESH PRODUCTS
        # ==================================================

        products = Product.query.order_by(
            Product.id.desc()
        ).all()

        # ==================================================
        # ✅ SUCCESS MESSAGE
        # ==================================================

        flash(
            (
                "✅ تم إضافة المنتج بنجاح!"
                if current_lang == "ar"
                else "✅ Product added successfully!"
            ),
            "success"
        )

        # ==================================================
        # ↩️ REDIRECT
        # ==================================================

        return redirect(
            url_for("admin_products")
        )

    # ==================================================
    # 🖥️ DISPLAY PRODUCTS PAGE
    # ==================================================

    return render_template(
        "admin/add_product.html",
        form=form,
        products=products
    )
# ==========================================
# ✏️ ADD / EDIT PRODUCT
# ==========================================

@app.route("/admin/product", methods=["GET", "POST"])
@app.route("/admin/product/<int:product_id>", methods=["GET", "POST"])
@login_required
def add_or_edit_product(product_id=None):

    # ==========================================
    # 🔐 ADMIN CHECK
    # ==========================================

    if current_user.role != "admin":

        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )

        return redirect(
            url_for("home_logged")
        )

    # ==========================================
    # ✏️ EDIT MODE
    # ==========================================

    edit_mode = product_id is not None

    product = None

    if edit_mode:

        product = Product.query.get_or_404(
            product_id
        )

    # ==========================================
    # 📝 FORM
    # ==========================================

    form = AddProductForm(
        obj=product
    )

    # ==========================================
    # ✅ SUBMIT
    # ==========================================

    if form.validate_on_submit():

        # ======================================
        # 📦 PRODUCT DATA
        # ======================================

        name = form.name.data

        price = form.price.data

        description = form.description.data

        publish_location = (
            form.publish_location.data
        )

        # ======================================
        # 🖼️ IMAGE
        # ======================================

        image_file = form.image.data

        filename = (
            product.image
            if edit_mode and product.image
            else None
        )

        # ======================================
        # 🖼️ NEW IMAGE
        # ======================================

        if (
            image_file
            and image_file.filename
            and allowed_file(
                image_file.filename
            )
        ):

            filename = secure_filename(
                image_file.filename
            )

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "uploads",
                "products"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            image_path = os.path.join(
                upload_folder,
                filename
            )

            image_file.save(
                image_path
            )

        # ======================================
        # ✏️ UPDATE EXISTING PRODUCT
        # ======================================

        if edit_mode:

            product.name = name

            product.price = price

            product.description = description

            product.publish_location = (
                publish_location
            )

            product.image = filename

            flash(
                (
                    "✅ تم تعديل المنتج بنجاح!"
                    if current_lang == "ar"
                    else "✅ Product updated successfully!"
                ),
                "success"
            )

        # ======================================
        # ➕ ADD NEW PRODUCT
        # ======================================

        else:

            new_product = Product(

                name=name,

                price=price,

                description=description,

                image=filename,

                publish_location=
                    publish_location,

                is_new=True,

                stock=1,

                purchase_count=0,

                is_customizable=False
            )

            db.session.add(
                new_product
            )

            flash(
                (
                    "🧶 تم إضافة المنتج بنجاح!"
                    if current_lang == "ar"
                    else "🧶 Product added successfully!"
                ),
                "success"
            )

        # ======================================
        # 💾 SAVE
        # ======================================

        db.session.commit()

        # ======================================
        # ↩️ BACK TO PRODUCTS
        # ======================================

        return redirect(
            url_for("admin_products")
        )

    # ==========================================
    # 🖥️ PAGE
    # ==========================================

    return render_template(

        "add_product.html",

        form=form,

        edit_mode=edit_mode,

        product=product
    )

# ==================================================
# 🧸 PRODUCT DETAILS
# ==================================================

@app.route("/product/<int:product_id>")
@login_required
def product_details(product_id):

    # ==========================================
    # 🧸 البحث عن المنتج
    # ==========================================

    product = Product.query.get_or_404(product_id)


    # ==========================================
    # 🧸 المنتجات المرتبطة
    # نفس التصنيف
    # ==========================================

    related_products = Product.query.filter(

        Product.category == product.category,

        Product.id != product.id

    ).limit(4).all()


    # ==========================================
    # 👤 المستخدم الحالي
    # ==========================================

    user_id = session.get("user_id")


    # ==========================================
    # ❤️ المنتجات الموجودة في المفضلة
    # للمستخدم الحالي
    # ==========================================

    wishlist_ids = set()

    if user_id:

        wishlist_items = Wishlist.query.filter_by(
            user_id=user_id
        ).all()

        wishlist_ids = {

            item.product_id

            for item in wishlist_items

        }


    # ==========================================
    # 👥 عدد مرات شراء المنتج
    #
    # نستخدم purchase_count الموجود
    # داخل Product
    # ==========================================

    purchased_count = product.purchase_count or 0


    # ==========================================
    # 🧾 عرض صفحة تفاصيل المنتج
    # ==========================================

    return render_template(

        "product_details.html",

        product=product,

        related_products=related_products,

        wishlist_ids=wishlist_ids,

        purchased_count=purchased_count

    )




# ==========================================
# 🎨 UPLOAD CUSTOMIZATION REFERENCE IMAGE
# ==========================================

@app.route("/api/customization/upload-image", methods=["POST"])
@login_required
def upload_customization_reference_image():
    image = request.files.get("reference_image")

    if not image or not image.filename:
        return jsonify({
            "success": False,
            "error": "No image selected."
        }), 400

    extension = os.path.splitext(image.filename)[1].lower()

    if extension not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return jsonify({
            "success": False,
            "error": "Only image files are allowed."
        }), 400

    filename = uuid.uuid4().hex + extension

    upload_folder = os.path.join(
        app.root_path,
        "static",
        "uploads",
        "customization"
    )

    os.makedirs(upload_folder, exist_ok=True)

    image.save(os.path.join(upload_folder, filename))

    return jsonify({
        "success": True,
        "url": url_for(
            "static",
            filename=f"uploads/customization/{filename}"
        )
    }), 200


# ==========================================
# 📦 ORDER DETAILS API
# ==========================================

@app.route("/api/order/<int:order_id>")
def get_order_details(order_id):

    order = Order.query.get(order_id)

    if not order:
        return jsonify({
            "error": "Order not found"
        }), 404


    items = (
        db.session.query(OrderItem, Product)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(OrderItem.order_id == order.id)
        .all()
    )


    item_list = []


    for order_item, product in items:

        item_list.append({
            "name": product.name,
            "price": order_item.price,
            "quantity": order_item.quantity,

            # 📏 الحجم المختار
            "selected_size": (
                order_item.selected_size
                if hasattr(order_item, "selected_size")
                else None
            ),

            # 🎨 تفاصيل التخصيص
            "customization": (
                order_item.customization
                if hasattr(order_item, "customization")
                else None
            ),

            "image": product.image if product.image else ""
        })


    return jsonify({
        "id": order.id,
        "customer_name": order.customer_name,
        "customer_email": order.customer_email,
        "address": order.address,
        "payment_method": order.payment_method,
        "status": order.status,

        "created_at": (
            order.created_at.strftime("%Y-%m-%d %H:%M")
            if order.created_at
            else ""
        ),

        "total": order.total,
        "items": item_list
    })

# ==========================================
# 📦 GET USER ORDERS BY STATUS
# ==========================================




# ==========================================
# 📦 CUSTOMER ORDER DETAILS
# ==========================================

@app.route("/my-order/<int:order_id>")
@login_required
def customer_order_detail(order_id):

    # ==========================================
    # 🔐 GET ONLY THE CURRENT USER'S ORDER
    # ==========================================

    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user.id
    ).first_or_404()


    # ==========================================
    # 🎨 PREPARE CUSTOMIZATION DATA
    # ==========================================

    import json

    for item in order.items:

        item.customization_data = {}

        if item.customization:

            try:

                if isinstance(item.customization, str):

                    item.customization_data = json.loads(
                        item.customization
                    )

                elif isinstance(item.customization, dict):

                    item.customization_data = (
                        item.customization
                    )

            except (json.JSONDecodeError, TypeError, ValueError):

                item.customization_data = {}


    # ==========================================
    # 🧾 ORDER DETAILS PAGE
    # ==========================================

    return render_template(
        "customer_order_detail.html",
        order=order
    )
# ==========================================
# ❤️ TOGGLE WISHLIST
# ==========================================

@app.route("/wishlist/<int:product_id>", methods=["POST"])
@login_required
def toggle_wishlist(product_id):

    product = Product.query.get_or_404(product_id)

    item = Wishlist.query.filter_by(
        user_id=current_user.id,
        product_id=product.id
    ).first()

    if item:
        db.session.delete(item)
        flash("💔 Removed from wishlist.", "info")
    else:
        wishlist = Wishlist(
            user_id=current_user.id,
            product_id=product.id
        )

        db.session.add(wishlist)
        flash("❤️ Added to wishlist.", "success")

    db.session.commit()

    return redirect(request.referrer or url_for("products_page"))
    
# ==========================================
# ❤️ WISHLIST PAGE
# ==========================================

@app.route("/wishlist")
@login_required
def wishlist_page():

    wishlist = Wishlist.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "wishlist.html",
        wishlist=wishlist
    )
# ==========================================
# 🏠 GENERAL ROUTES
# ==========================================
@app.route("/", methods=["GET", "POST"])
def index():

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    # جميع التقييمات
    reviews = Review.query.order_by(Review.id.desc()).all()

    form = LoginForm()
    register_form = RegisterForm()
    verify_form = VerifyCodeForm()

    login_error = False

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data
        ).first()

        # البريد الإلكتروني غير موجود
        if not user:

            login_error = True

            if session.get("language") == "ar":
                flash("❌ البريد الإلكتروني غير موجود.", "login_error")
            else:
                flash("❌ Email not found.", "login_error")

        # كلمة المرور خاطئة
        elif not user.check_password(form.password.data):

            login_error = True

            if session.get("language") == "ar":
                flash("❌ كلمة المرور غير صحيحة.", "login_error")
            else:
                flash("❌ Incorrect password.", "login_error")

        # تسجيل الدخول
        else:

            login_user(user)
            session["is_admin"] = (user.role == "admin")

            merge_session_cart_into_db(user.id)

            if user.role == "admin":
                return redirect(url_for("admin_home"))

            return redirect(url_for("home_logged"))

    return render_template(
        "index.html",
        products=products,
        reviews=reviews,
        form=form,
        register_form=register_form,
        verify_form=verify_form,
        login_error=login_error
    )

# ==========================================
# 👤 REGISTER
# ==========================================

# ==========================================
# 👤 REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        # ==========================================
        # 📧 التحقق من صيغة البريد الإلكتروني
        # ==========================================
        email_pattern = (
            r"^[A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\."
            r"[A-Za-z]{2,}$"
        )

        if not re.match(email_pattern, email):
            form.email.errors.append(
                "صيغة البريد الإلكتروني غير صحيحة. مثال: example@gmail.com"
            )

            login_form = LoginForm()
            verify_form = VerifyCodeForm()
            products = Product.query.filter(
                Product.publish_location.in_(["both", "home_only"])
            ).all()

            return render_template(
                "index.html",
                products=products,
                form=login_form,
                register_form=form,
                verify_form=verify_form,
                show_register_popup=True
            )

        # ==========================================
        # 📧 البريد الإلكتروني يجب أن يكون فريدًا
        # ==========================================
        existing_email = User.query.filter(
            func.lower(User.email) == email
        ).first()

        if existing_email:
            form.email.errors.append(
                "هذا البريد الإلكتروني مسجل بالفعل."
            )

            login_form = LoginForm()
            verify_form = VerifyCodeForm()
            products = Product.query.filter(
                Product.publish_location.in_(["both", "home_only"])
            ).all()

            return render_template(
                "index.html",
                products=products,
                form=login_form,
                register_form=form,
                verify_form=verify_form,
                show_register_popup=True
            )

        # ==========================================
        # 👤 إنشاء المستخدم
        # اسم المستخدم مسموح يتكرر
        # البريد الإلكتروني فقط يجب أن يكون فريدًا
        # ==========================================
        new_user = User(
            username=username,
            email=email,
            phone=form.phone.data,
            confirmed=True
        )

        # ==========================================
        # 🔐 تشفير كلمة المرور
        # ==========================================
        new_user.set_password(form.password.data)

        # ==========================================
        # 👑 تحديد الأدمن
        # ==========================================
        if email == "admin@store.com":
            new_user.role = "admin"
        else:
            new_user.role = "user"

        # ==========================================
        # 💾 حفظ المستخدم
        # ==========================================
        try:
            db.session.add(new_user)
            db.session.commit()

        except Exception as e:
            db.session.rollback()

            print(f"❌ Registration error: {e}")

            # البريد الإلكتروني ما زال فريدًا في قاعدة البيانات
            if (
                "user_email_key" in str(e)
                or "UNIQUE constraint failed: user.email" in str(e)
            ):
                form.email.errors.append(
                    "هذا البريد الإلكتروني مسجل بالفعل."
                )

            else:
                form.email.errors.append(
                    "حدث خطأ أثناء إنشاء الحساب، حاول مرة أخرى."
                )

            login_form = LoginForm()
            verify_form = VerifyCodeForm()
            products = Product.query.filter(
                Product.publish_location.in_(["both", "home_only"])
            ).all()

            return render_template(
                "index.html",
                products=products,
                form=login_form,
                register_form=form,
                verify_form=verify_form,
                show_register_popup=True
            )

        print(f"✅ New user saved: {new_user.email}")

        # ==========================================
        # 🔗 ربط الزيارة الحالية بالمستخدم
        # ==========================================
        current_visitor_id = session.get("visitor_id")

        if current_visitor_id:
            current_visit = (
                Visitor.query
                .filter_by(visitor_id=current_visitor_id)
                .first()
            )

            if current_visit:
                current_visit.user_id = new_user.id
                current_visit.visitor_type = "registered"
                current_visit.page = request.path
                current_visit.last_activity = datetime.utcnow()

                db.session.commit()

                print(
                    f"👤 VISIT LINKED TO USER: "
                    f"{current_visitor_id} → User #{new_user.id}"
                )
            else:
                print(
                    f"⚠️ Visitor not found: {current_visitor_id}"
                )
        else:
            print("⚠️ No visitor_id found in session")

        # ==========================================
        # 🔐 تسجيل الدخول مباشرة بعد إنشاء الحساب
        # لا يوجد تحقق بالإيميل
        # ==========================================
        login_user(new_user)
        session["is_admin"] = (new_user.role == "admin")

        # نقل سلة الزائر إلى حسابه
        merge_session_cart_into_db(new_user.id)

        # ==========================================
        # ✅ رسالة نجاح
        # ==========================================
        if session.get("language") == "ar":
            flash(
                "💕 تم إنشاء حسابك وتسجيل دخولك بنجاح!",
                "success"
            )
        else:
            flash(
                "💕 Your account was created and you are now logged in!",
                "success"
            )

        # ==========================================
        # 👑 الأدمن → لوحة التحكم
        # 👤 العميل → الصفحة الرئيسية بعد تسجيل الدخول
        # ==========================================
        if new_user.role == "admin":
            return redirect(url_for("admin_home"))

        return redirect(url_for("home_logged"))

    # ==========================================
    # GET / Validation Failed
    # ==========================================
    login_form = LoginForm()
    verify_form = VerifyCodeForm()

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    return render_template(
        "index.html",
        products=products,
        register_form=form,
        form=login_form,
        verify_form=verify_form
    )

@app.route("/forgot_password", methods=["POST"])
def forgot_password():
    flash(
        "Password recovery by email is currently unavailable.",
        "danger"
    )
    return redirect(url_for("index"))


@app.route("/verify_reset_code", methods=["POST"])
def verify_reset_code():
    flash(
        "Email verification is no longer required.",
        "info"
    )
    return redirect(url_for("index"))


@app.route("/verify_email", methods=["GET", "POST"])
def verify_email():
    flash(
        "Email verification is no longer required.",
        "info"
    )
    return redirect(url_for("index"))


@app.route("/reset_password", methods=["POST"])
def reset_password():
    flash(
        "Password recovery by email is currently unavailable.",
        "danger"
    )
    return redirect(url_for("index"))

@app.route("/change_password", methods=["POST"])
@login_required
def change_password():

    current = request.form["current_password"]
    new = request.form["new_password"]
    confirm = request.form["confirm_password"]

    if not current_user.check_password(current):
        flash("كلمة المرور الحالية غير صحيحة", "danger")
        return redirect(url_for("profile"))

    if new != confirm:
        flash("كلمتا المرور غير متطابقتين", "danger")
        return redirect(url_for("profile"))

    current_user.set_password(new)

    db.session.commit()

    flash("تم تغيير كلمة المرور بنجاح", "success")

    return redirect(url_for("profile"))
@app.route("/add-review", methods=["POST"])
@login_required
def add_review():

    review = Review(
        name=current_user.username,
        message=request.form.get("message"),
        stars=int(request.form.get("stars"))
    )

    db.session.add(review)
    db.session.commit()

    flash("تم إرسال تقييمك بنجاح 💕")

    return redirect(url_for("home_logged"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    # ==========================
    # Statistics
    # ==========================

    total_orders = Order.query.filter_by(
        user_id=current_user.id
    ).count()

    pending_payment_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending Payment"
    ).count()

    pending_review_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending Review"
    ).count()

    processing_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Processing"
    ).count()

    shipping_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Shipping"
    ).count()

    delivered_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Delivered"
    ).count()

    cancelled_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Cancelled"
    ).count()

    cart_count = Cart.query.filter_by(
        user_id=current_user.id
    ).count()

    wishlist_count = Wishlist.query.filter_by(
        user_id=current_user.id
    ).count()

    # ==========================
    # Orders Lists
    # ==========================

    all_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Order.created_at.desc()
    ).all()

    pending_payment_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending Payment"
    ).order_by(
        Order.created_at.desc()
    ).all()

    pending_review_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending Review"
    ).order_by(
        Order.created_at.desc()
    ).all()

    processing_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Processing"
    ).order_by(
        Order.created_at.desc()
    ).all()

    shipping_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Shipping"
    ).order_by(
        Order.created_at.desc()
    ).all()

    delivered_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Delivered"
    ).order_by(
        Order.created_at.desc()
    ).all()

    cancelled_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Cancelled"
    ).order_by(
        Order.created_at.desc()
    ).all()

    # ==========================
    # Update Profile
    # ==========================

    if request.method == "POST":

        current_user.username = request.form.get("username")
        current_user.email = request.form.get("email")
        current_user.phone = request.form.get("phone")
        current_user.birthday = request.form.get("birthday")
        current_user.gender = request.form.get("gender")
        current_user.nationality = request.form.get("nationality")

        # ==========================
        # Upload Profile Image
        # ==========================

        image = request.files.get("profile_image")

        if image and image.filename != "":

            filename = secure_filename(image.filename)

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "uploads",
                "profile"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            image_path = os.path.join(
                upload_folder,
                filename
            )

            image.save(image_path)

            current_user.profile_image = filename

        # ==========================
        # Save Changes
        # ==========================

        db.session.commit()

        # ==========================
        # Success Message
        # ==========================

        flash(
            "profile_updated_successfully",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    # ==========================
    # Render Profile
    # ==========================

    return render_template(
        "profile.html",

        user=current_user,

        total_orders=total_orders,
        pending_payment_orders=pending_payment_orders,
        pending_review_orders=pending_review_orders,
        processing_orders=processing_orders,
        shipping_orders=shipping_orders,
        delivered_orders=delivered_orders,
        cancelled_orders=cancelled_orders,

        cart_count=cart_count,
        wishlist_count=wishlist_count,

        orders=all_orders,

        pending_payment_list=pending_payment_list,
        pending_review_list=pending_review_list,
        processing_list=processing_list,
        shipping_list=shipping_list,
        delivered_list=delivered_list,
        cancelled_list=cancelled_list
    )

@app.route("/delete-account", methods=["POST"])
@login_required
def delete_account():

    try:
        user = current_user
        user_id = user.id

        # ==========================
        # Delete Cart
        # ==========================

        Cart.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )


        # ==========================
        # Delete Wishlist
        # ==========================

        Wishlist.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )


        # ==========================
        # Get User Orders
        # ==========================

        orders = Order.query.filter_by(
            user_id=user_id
        ).all()

        order_ids = [
            order.id
            for order in orders
        ]


        # ==========================
        # Delete Order Items First
        # ==========================

        if order_ids:

            OrderItem.query.filter(
                OrderItem.order_id.in_(order_ids)
            ).delete(
                synchronize_session=False
            )


        # ==========================
        # Delete Orders
        # ==========================

        Order.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )


        # ==========================
        # Delete Visitor Records
        # ==========================

        Visitor.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )


        # ==========================
        # Delete User
        # ==========================

        db.session.delete(user)

        db.session.commit()


        # ==========================
        # Logout
        # ==========================

        logout_user()


        flash(
            "account_deleted_successfully",
            "success"
        )


        return redirect(
            url_for("home_logged")
        )


    except Exception as e:

        db.session.rollback()

        print(
            "DELETE ACCOUNT ERROR:",
            repr(e)
        )


        flash(
            "account_delete_failed",
            "error"
        )


        return redirect(
            url_for("profile")
        )
# ==================================================
# 📢 ADVERTISEMENTS
# ==================================================

@app.route("/admin/advertisements")
@login_required
def admin_advertisements():

    if current_user.role != "admin":
        return redirect(url_for("home_logged"))

    advertisements = Advertisement.query.order_by(
        Advertisement.display_order.asc(),
        Advertisement.id.asc()
    ).all()

    return render_template(
        "admin/advertisements.html",
        advertisements=advertisements
    )


# ==================================================
# ➕ ADD ADVERTISEMENT
# ==================================================

@app.route(
    "/admin/advertisements/add",
    methods=["GET", "POST"]
)
@login_required
def admin_add_advertisement():

    if current_user.role != "admin":
        return redirect(
            url_for("home_logged")
        )

    current_lang = session.get(
        "language",
        "ar"
    )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        image = request.files.get("image")

        # ------------------------------------------
        # CHECK IMAGE
        # ------------------------------------------

        if not image or not image.filename:

            flash(
                "Please select an image."
                if current_lang != "ar"
                else "الرجاء اختيار صورة للإعلان.",
                "error"
            )

            return redirect(
                url_for("admin_add_advertisement")
            )

        # ------------------------------------------
        # CHECK EXTENSION
        # ------------------------------------------

        extension = os.path.splitext(
            image.filename
        )[1].lower()

        allowed_extensions = {
            ".jpg",
            ".jpeg",
            ".png"
        }

        if extension not in allowed_extensions:

            flash(
                "Only JPG and PNG images are allowed."
                if current_lang != "ar"
                else "يسمح فقط بصور JPG و PNG.",
                "error"
            )

            return redirect(
                url_for("admin_add_advertisement")
            )

        # ------------------------------------------
        # GENERATE FILE NAME
        # ------------------------------------------

        filename = (
            uuid.uuid4().hex
            + extension
        )

        # ------------------------------------------
        # UPLOAD FOLDER
        # ------------------------------------------

        upload_folder = os.path.join(
            app.root_path,
            "static",
            "images",
            "advertisements"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        # ------------------------------------------
        # SAVE IMAGE
        # ------------------------------------------

        image.save(
            os.path.join(
                upload_folder,
                filename
            )
        )

        # ------------------------------------------
        # TITLE
        # ------------------------------------------

        title = request.form.get(
            "title",
            ""
        ).strip()

        # ------------------------------------------
        # DISPLAY ORDER
        # ------------------------------------------

        try:

            display_order = int(
                request.form.get(
                    "display_order",
                    0
                ) or 0
            )

        except (ValueError, TypeError):

            display_order = 0

        # ------------------------------------------
        # CREATE ADVERTISEMENT
        # ------------------------------------------

        advertisement = Advertisement(
            image=filename,
            title=title,
            display_order=display_order,
            is_active=True
        )

        db.session.add(
            advertisement
        )

        db.session.commit()

        # ------------------------------------------
        # SUCCESS
        # ------------------------------------------

        flash(
            "Advertisement added successfully."
            if current_lang != "ar"
            else "تمت إضافة الإعلان بنجاح.",
            "success"
        )

        return redirect(
            url_for("admin_advertisements")
        )

    # ==================================================
    # GET
    # ==================================================

    return render_template(
        "admin/add_advertisement.html"
    )


# ==================================================
# ✏️ EDIT ADVERTISEMENT
# ==================================================

@app.route(
    "/admin/advertisements/edit/<int:ad_id>",
    methods=["GET", "POST"]
)
@login_required
def admin_edit_advertisement(ad_id):

    if current_user.role != "admin":
        return redirect(
            url_for("home_logged")
        )

    current_lang = session.get(
        "language",
        "ar"
    )

    advertisement = Advertisement.query.get_or_404(
        ad_id
    )

    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # ------------------------------------------
        # TITLE
        # ------------------------------------------

        advertisement.title = request.form.get(
            "title",
            ""
        ).strip()

        # ------------------------------------------
        # DISPLAY ORDER
        # ------------------------------------------

        try:

            advertisement.display_order = int(
                request.form.get(
                    "display_order",
                    0
                ) or 0
            )

        except (ValueError, TypeError):

            advertisement.display_order = 0

        # ------------------------------------------
        # ACTIVE STATUS
        # ------------------------------------------

        advertisement.is_active = (
            request.form.get("is_active") == "1"
        )

        # ------------------------------------------
        # NEW IMAGE
        # ------------------------------------------

        image = request.files.get("image")

        if image and image.filename:

            extension = os.path.splitext(
                image.filename
            )[1].lower()

            allowed_extensions = {
                ".jpg",
                ".jpeg",
                ".png"
            }

            # ------------------------------------------
            # CHECK EXTENSION
            # ------------------------------------------

            if extension not in allowed_extensions:

                flash(
                    "Only JPG and PNG images are allowed."
                    if current_lang != "ar"
                    else "يسمح فقط بصور JPG و PNG.",
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_edit_advertisement",
                        ad_id=ad_id
                    )
                )

            # ------------------------------------------
            # UPLOAD FOLDER
            # ------------------------------------------

            upload_folder = os.path.join(
                app.root_path,
                "static",
                "images",
                "advertisements"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            # ------------------------------------------
            # DELETE OLD IMAGE
            # ------------------------------------------

            if advertisement.image:

                old_path = os.path.join(
                    upload_folder,
                    advertisement.image
                )

                if os.path.exists(old_path):

                    try:
                        os.remove(old_path)

                    except OSError:
                        pass

            # ------------------------------------------
            # NEW FILE NAME
            # ------------------------------------------

            filename = (
                uuid.uuid4().hex
                + extension
            )

            # ------------------------------------------
            # SAVE NEW IMAGE
            # ------------------------------------------

            image.save(
                os.path.join(
                    upload_folder,
                    filename
                )
            )

            advertisement.image = filename

        # ------------------------------------------
        # SAVE
        # ------------------------------------------

        db.session.commit()

        flash(
            "Advertisement updated successfully."
            if current_lang != "ar"
            else "تم تعديل الإعلان بنجاح.",
            "success"
        )

        return redirect(
            url_for("admin_advertisements")
        )

    # ==================================================
    # GET
    # ==================================================

    return render_template(
        "admin/edit_advertisement.html",
        advertisement=advertisement
    )


# ==================================================
# 🔄 TOGGLE ADVERTISEMENT
# ==================================================

@app.route(
    "/admin/advertisements/toggle/<int:ad_id>",
    methods=["POST"]
)
@login_required
def admin_toggle_advertisement(ad_id):

    if current_user.role != "admin":
        return redirect(
            url_for("home_logged")
        )

    current_lang = session.get(
        "language",
        "ar"
    )

    advertisement = Advertisement.query.get_or_404(
        ad_id
    )

    # ------------------------------------------
    # TOGGLE STATUS
    # ------------------------------------------

    advertisement.is_active = not advertisement.is_active

    db.session.commit()

    # ------------------------------------------
    # MESSAGE
    # ------------------------------------------

    if advertisement.is_active:

        flash(
            "Advertisement enabled successfully."
            if current_lang != "ar"
            else "تم تفعيل الإعلان بنجاح.",
            "success"
        )

    else:

        flash(
            "Advertisement disabled successfully."
            if current_lang != "ar"
            else "تم تعطيل الإعلان بنجاح.",
            "success"
        )

    return redirect(
        url_for("admin_advertisements")
    )


# ==================================================
# 🗑️ DELETE ADVERTISEMENT
# ==================================================

@app.route(
    "/admin/advertisements/delete/<int:ad_id>",
    methods=["POST"]
)
@login_required
def admin_delete_advertisement(ad_id):

    if current_user.role != "admin":
        return redirect(
            url_for("home_logged")
        )

    current_lang = session.get(
        "language",
        "ar"
    )

    advertisement = Advertisement.query.get_or_404(
        ad_id
    )

    # ------------------------------------------
    # DELETE IMAGE
    # ------------------------------------------

    if advertisement.image:

        upload_folder = os.path.join(
            app.root_path,
            "static",
            "images",
            "advertisements"
        )

        image_path = os.path.join(
            upload_folder,
            advertisement.image
        )

        if os.path.exists(image_path):

            try:
                os.remove(image_path)

            except OSError:
                pass

    # ------------------------------------------
    # DELETE DATABASE RECORD
    # ------------------------------------------

    db.session.delete(
        advertisement
    )

    db.session.commit()

    # ------------------------------------------
    # SUCCESS MESSAGE
    # ------------------------------------------

    flash(
        "Advertisement deleted successfully."
        if current_lang != "ar"
        else "تم حذف الإعلان بنجاح.",
        "success"
    )

    return redirect(
        url_for("admin_advertisements")
    )
# ==========================================
# 📦 GET USER ORDERS BY STATUS
# ==========================================

@app.route("/get-orders/<status>")
@login_required
def get_orders(status):

    print("STATUS =", status)

    orders = Order.query.filter_by(
        user_id=current_user.id,
        status=status
    ).order_by(
        Order.created_at.desc()
    ).all()

    result = []

    for order in orders:

        items = []

        for item in order.items:

            items.append({
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price": item.price
            })

        result.append({
            "id": order.id,
            "total": order.total,
            "status": order.status,
            "date": order.created_at.strftime("%Y-%m-%d"),
            "shipping_company": order.shipping_company,
            "tracking_number": order.tracking_number,
            "items": items
        })

    return jsonify(result)
@app.route("/upload_profile_image", methods=["POST"])
@login_required
def upload_profile_image():

    image = request.files.get("profile_image")

    if not image or image.filename == "":
        return {"success": False}

    filename = secure_filename(image.filename)

    upload_folder = os.path.join(
        app.root_path,
        "static",
        "uploads",
        "profile"
    )

    os.makedirs(upload_folder, exist_ok=True)

    image.save(
        os.path.join(upload_folder, filename)
    )

    current_user.profile_image = filename

    db.session.commit()

    return {"success": True}
# ==========================================
# 🔐 LOGIN
# ==========================================

# ==========================================
# 🔐 LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()
    register_form = RegisterForm()
    verify_form = VerifyCodeForm()

    products = Product.query.filter(
        Product.publish_location.in_(
            ["both", "home_only"]
        )
    ).all()

    # ==========================================
    # 🔐 معالجة تسجيل الدخول
    # ==========================================
    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        user = User.query.filter(
            func.lower(User.email) == email
        ).first()

        # ==========================================
        # ❌ البريد الإلكتروني غير موجود
        # ==========================================
        if user is None:

            if session.get("language") == "ar":
                flash(
                    "❌ البريد الإلكتروني غير موجود.",
                    "login_error"
                )
            else:
                flash(
                    "❌ Email not found.",
                    "login_error"
                )

            return render_template(
                "index.html",
                products=products,
                form=form,
                register_form=register_form,
                verify_form=verify_form,
                login_error=True
            )

        # ==========================================
        # ❌ كلمة المرور خاطئة
        # ==========================================
        if not user.check_password(
            form.password.data
        ):

            if session.get("language") == "ar":
                flash(
                    "❌ كلمة المرور غير صحيحة.",
                    "login_error"
                )
            else:
                flash(
                    "❌ Incorrect password.",
                    "login_error"
                )

            return render_template(
                "index.html",
                products=products,
                form=form,
                register_form=register_form,
                verify_form=verify_form,
                login_error=True
            )

        # ==========================================
        # 📧 البريد غير مؤكد
        # ==========================================
        if not user.confirmed:

            session["verification_email"] = user.email

            # ==========================================
            # إذا كان عنده كود صالح مسبقًا
            # لا نرسل كود جديد
            # ==========================================
            if (
                user.verification_code
                and user.verification_expiry
                and datetime.utcnow()
                < user.verification_expiry
            ):
                pass

            else:

                # ==========================================
                # 🔢 إنشاء كود تحقق جديد
                # ==========================================
                verification_code = (
                    str(
                        secrets.randbelow(
                            1000000
                        )
                    ).zfill(6)
                )

                user.verification_code = (
                    verification_code
                )

                user.verification_expiry = (
                    datetime.utcnow()
                    + timedelta(minutes=10)
                )

                db.session.commit()

                # ==========================================
                # 📧 إرسال الكود باستخدام Resend
                # ==========================================
                email_sent = (
                    send_verification_email(
                        user.email,
                        verification_code
                    )
                )

                # ==========================================
                # ❌ فشل إرسال الإيميل
                # ==========================================
                if not email_sent:

                    if session.get("language") == "ar":
                        flash(
                            "❌ تعذر إرسال رمز التحقق. حاول مرة أخرى.",
                            "login_error"
                        )
                    else:
                        flash(
                            "❌ Could not send verification code. Please try again.",
                            "login_error"
                        )

                    return render_template(
                        "index.html",
                        products=products,
                        form=form,
                        register_form=register_form,
                        verify_form=verify_form,
                        login_error=True
                    )

            # ==========================================
            # 🚫 لا تسمح بالدخول
            # ==========================================
            if session.get("language") == "ar":
                flash(
                    "📧 يجب تأكيد بريدك الإلكتروني أولًا. تم إرسال رمز التحقق إلى بريدك.",
                    "login_error"
                )
            else:
                flash(
                    "📧 Please verify your email first. A verification code has been sent to your email.",
                    "login_error"
                )

            return redirect(
                url_for(
                    "index",
                    verify="1"
                )
            )

        # ==========================================
        # ✅ البريد مؤكد
        # ==========================================
        login_user(
            user,
            remember=True
        )

        session["user_id"] = user.id

        session["is_admin"] = (
            user.role == "admin"
        )

        # ==========================================
        # 👀 ربط الزيارة بالمستخدم
        # ==========================================
        current_visitor_id = session.get(
            "visitor_id"
        )

        if current_visitor_id:

            current_visit = (
                Visitor.query
                .filter_by(
                    visitor_id=current_visitor_id
                )
                .first()
            )

            if current_visit:

                current_visit.user_id = (
                    user.id
                )

                current_visit.visitor_type = (
                    "registered"
                )

                current_visit.last_activity = (
                    datetime.utcnow()
                )

                db.session.commit()

        # ==========================================
        # 🛒 دمج السلة
        # ==========================================
        merge_session_cart_into_db(
            user.id
        )

        # ==========================================
        # 👑 Admin
        # ==========================================
        if user.role == "admin":

            return redirect(
                url_for(
                    "admin_home"
                )
            )

        # ==========================================
        # 👤 User
        # ==========================================
        return redirect(
            url_for(
                "home_logged"
            )
        )

    # ==========================================
    # GET / نموذج غير صالح
    # ==========================================
    if request.method == "POST":

        if session.get("language") == "ar":
            flash(
                "❌ يرجى التحقق من البيانات.",
                "login_error"
            )
        else:
            flash(
                "❌ Please check your information.",
                "login_error"
            )

    return render_template(
        "index.html",
        products=products,
        form=form,
        register_form=register_form,
        verify_form=verify_form,
        login_error=True
    )

# ==========================================
# 🚪 LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():

    print(
        "Before logout:",
        current_user.is_authenticated
    )

    logout_user()

    print(
        "After logout:",
        current_user.is_authenticated
    )

    # ==========================
    # Logout Message
    # ==========================

    if session.get("lang", "ar") == "ar":

        flash(
            "👋 تم تسجيل الخروج بنجاح.",
            "success"
        )

    else:

        flash(
            "👋 You have been logged out successfully.",
            "success"
        )

    return redirect(
        url_for("index")
    )

# ==========================================
# 🛒 CART PAGE
# ==========================================

@app.route("/cart")
@login_required
def cart_page():
    return render_template("cart.html")
# ==========================================
# 🛒 CART API
# ==========================================

# ==================================================
# 🛒 ADD / UPDATE CART
# ==================================================

@app.route("/api/cart/add", methods=["POST"])
@login_required
def api_cart_add():

    # ==========================================
    # الحصول على البيانات
    # ==========================================

    data = request.get_json() or {}

    product_id = data.get("product_id")

    selected_size = data.get(
        "size",
        data.get("selected_size")
    )

    customization = data.get(
        "customization"
    )

    # ==========================================
    # 🎨 تنظيف بيانات التخصيص
    # ==========================================

    if customization in [None, "", {}, []]:
        customization = None

    # تحويل التخصيص إلى JSON
    # حتى يتم حفظه داخل قاعدة البيانات
    elif isinstance(customization, (dict, list)):

        try:
            customization = json.dumps(
                customization,
                ensure_ascii=False
            )

        except (TypeError, ValueError):

            customization = None

    else:

        customization = str(
            customization
        ).strip()

        if not customization:
            customization = None

    # ==========================================
    # تنظيف الحجم
    # ==========================================

    if selected_size is not None:

        selected_size = str(
            selected_size
        ).strip()

        if not selected_size:
            selected_size = None

    # ==========================================
    # الكمية
    # ==========================================

    try:

        quantity = int(
            data.get(
                "quantity",
                1
            )
        )

    except (TypeError, ValueError):

        quantity = 1

    # ==========================================
    # التحقق من product_id
    # ==========================================

    if not product_id:

        return jsonify({

            "success": False,

            "error":
                "No product_id provided"

        }), 400

    # ==========================================
    # البحث عن المنتج
    # ==========================================

    product = Product.query.get(
        product_id
    )

    if not product:

        return jsonify({

            "success": False,

            "error":
                "Product not found"

        }), 404

    # ==========================================
    # التحقق من المستخدم
    # ==========================================

    user_id = session.get(
        "user_id"
    )

    if not user_id:

        return jsonify({

            "success": False,

            "error":
                "Please login first"

        }), 401

    # ==========================================
    # التحقق من الكمية
    # ==========================================

    if quantity == 0:

        return jsonify({

            "success": False,

            "error":
                "Quantity must be greater than zero"

        }), 400

    # ==========================================
    # 💰 تحديد السعر
    # ==========================================

    try:

        selected_price = float(
            product.price
        )

    except (
        TypeError,
        ValueError
    ):

        selected_price = 0

    size_prices = (
        product.size_prices
        or {}
    )

    # ==========================================
    # 📏 إذا تم اختيار حجم
    # ==========================================

    if selected_size:

        if selected_size in size_prices:

            try:

                selected_price = float(
                    size_prices[
                        selected_size
                    ]
                )

            except (
                TypeError,
                ValueError
            ):

                selected_price = float(
                    product.price
                )

        else:

            return jsonify({

                "success": False,

                "error":
                    "Selected size is not available"

            }), 400

    # ==========================================
    # إذا المنتج لا يحتوي أحجام
    # ==========================================

    else:

        selected_size = None

        try:

            selected_price = float(
                product.price
            )

        except (
            TypeError,
            ValueError
        ):

            selected_price = 0

    # ==========================================
    # 🔍 البحث عن المنتج داخل السلة
    #
    # مع مراعاة الحجم + التخصيص
    # ==========================================

    existing_query = Cart.query.filter_by(

        user_id=user_id,

        product_id=product_id

    )

    # ==========================================
    # 📏 فلترة الحجم
    # ==========================================

    if selected_size:

        existing_query = (
            existing_query.filter_by(
                selected_size=selected_size
            )
        )

    else:

        existing_query = (
            existing_query.filter(
                Cart.selected_size.is_(None)
            )
        )

    # ==========================================
    # 🎨 فلترة التخصيص
    #
    # كل تخصيص مختلف يعتبر طلبًا مختلفًا
    # ==========================================

    if customization:

        existing_query = (
            existing_query.filter_by(
                customization=customization
            )
        )

    else:

        existing_query = (
            existing_query.filter(
                Cart.customization.is_(None)
            )
        )

    existing = existing_query.first()

    # ==========================================
    # ➖ إنقاص الكمية
    #
    # إذا أرسلنا quantity = -1
    # ==========================================

    if quantity < 0:

        # المنتج غير موجود في السلة

        if not existing:

            return jsonify({

                "success": False,

                "error":
                    "Product is not in cart"

            }), 404

        # ==========================================
        # إنقاص الكمية
        # ==========================================

        existing.quantity += quantity

        # ==========================================
        # إذا وصلت الكمية إلى صفر
        # نحذف المنتج
        # ==========================================

        if existing.quantity <= 0:

            db.session.delete(
                existing
            )

            db.session.commit()

            return jsonify({

                "success": True,

                "message":
                    "Product removed from cart",

                "product_id":
                    product_id,

                "selected_size":
                    selected_size,

                "selected_price":
                    selected_price,

                "customization":
                    customization,

                "quantity":
                    0

            })

        # ==========================================
        # حفظ الكمية الجديدة
        # ==========================================

        db.session.commit()

        return jsonify({

            "success": True,

            "message":
                "Cart quantity decreased",

            "product_id":
                product_id,

            "selected_size":
                selected_size,

            "selected_price":
                selected_price,

            "customization":
                customization,

            "quantity":
                existing.quantity

        })

    # ==========================================
    # ➕ إضافة المنتج / زيادة الكمية
    # ==========================================

    if existing:

        # المنتج + الحجم + التخصيص
        # موجودين بالفعل

        existing.quantity += quantity

        # تأكيد السعر الحالي

        existing.selected_price = (
            selected_price
        )

        # تأكيد التخصيص

        existing.customization = (
            customization
        )

    else:

        # ==========================================
        # 🆕 إنشاء عنصر جديد في السلة
        # ==========================================

        new_item = Cart(

            user_id=user_id,

            product_id=product_id,

            quantity=quantity,

            selected_size=selected_size,

            selected_price=selected_price,

            customization=customization

        )

        db.session.add(
            new_item
        )

    # ==========================================
    # 💾 حفظ التغييرات
    # ==========================================

    db.session.commit()

    # ==========================================
    # 🔍 الحصول على العنصر الحالي
    # ==========================================

    current_query = Cart.query.filter_by(

        user_id=user_id,

        product_id=product_id

    )

    # ==========================================
    # 📏 فلترة الحجم
    # ==========================================

    if selected_size:

        current_query = (
            current_query.filter_by(
                selected_size=selected_size
            )
        )

    else:

        current_query = (
            current_query.filter(
                Cart.selected_size.is_(None)
            )
        )

    # ==========================================
    # 🎨 فلترة التخصيص
    # ==========================================

    if customization:

        current_query = (
            current_query.filter_by(
                customization=customization
            )
        )

    else:

        current_query = (
            current_query.filter(
                Cart.customization.is_(None)
            )
        )

    current_item = (
        current_query.first()
    )

    current_quantity = (

        current_item.quantity

        if current_item

        else 0

    )

    # ==========================================
    # النتيجة
    # ==========================================

    return jsonify({

        "success": True,

        "message":
            "Product added to cart",

        "product_id":
            product_id,

        "selected_size":
            selected_size,

        "selected_price":
            selected_price,

        "customization":
            customization,

        "quantity":
            current_quantity

    })
# ==========================================
# 🗑 REMOVE CART ITEM
# ==========================================

@app.route("/api/cart/remove", methods=["POST"])
@login_required
def api_cart_remove():

    data = request.get_json() or {}

    product_id = data.get("product_id")

    if not product_id:
        return jsonify({
            "success": False,
            "error": "No product_id provided"
        }), 400

    user_id = session.get("user_id")

    cart_item = Cart.query.filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()

    if not cart_item:

        return jsonify({
            "success": False,
            "error": "Product not found in cart"
        }), 404

    db.session.delete(cart_item)

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Product removed from cart"
    })


# ==========================================
# 🛒 GET CART
# ==========================================

@app.route("/api/cart")
@login_required
def api_cart_get():

    user_id = session.get("user_id")

    cart_items = Cart.query.filter_by(
        user_id=user_id
    ).all()

    output = []

    products_total = 0
    total_items = 0

    for item in cart_items:

        product = item.product

        if not product:
            continue

        quantity = item.quantity

        # ==========================================
        # 💰 SELECTED PRICE
        # ==========================================

        # إذا كان للعنصر سعر مقاس محفوظ
        # نستخدمه بدل السعر الأساسي

        if item.selected_price is not None:

            item_price = float(
                item.selected_price
            )

        else:

            item_price = float(
                product.price
            )

        # ==========================================
        # 🧮 ITEM TOTAL
        # ==========================================

        item_total = (
            item_price * quantity
        )

        products_total += item_total
        total_items += quantity

        # ==========================================
        # 📦 CART ITEM
        # ==========================================

        output.append({

            "id": product.id,

            "name": product.name,

            # السعر الفعلي للحجم المختار
            "price": item_price,

            # الحجم المختار
            "selected_size": (
                item.selected_size
                if item.selected_size
                else None
            ),

            # السعر المحفوظ للحجم
            "selected_price": item_price,

            # الكمية
            "quantity": quantity,

            # بيانات التخصيص
            "customization": item.customization,

            # المخزون
            "stock": product.stock,

            # الوصف
            "description": product.description,

            # الصورة
            "image": url_for(
                "static",
                filename=f"uploads/products/{product.image}"
            ) if product.image else "",

            # إجمالي العنصر
            "item_total": item_total
        })

    # ==========================================
    # 📤 RESPONSE
    # ==========================================

    return jsonify({

        "success": True,

        "cart": output,

        "products_total": products_total,

        "total_items": total_items

    })
# ==========================================
# ➕➖ Update Cart Quantity
# ==========================================

@app.route("/api/cart/update", methods=["POST"])
def api_cart_update():

    data = request.get_json() or {}

    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    if quantity < 1:
        quantity = 1

    user_id = session.get("user_id")

    # إذا المستخدم مسجل دخول
    if user_id:

        item = Cart.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()

        if item:
            item.quantity = quantity
            db.session.commit()

        return jsonify({
            "success": True
        })

    # إذا ضيف
    cart = session_get_cart()

    for item in cart:

        if item["product_id"] == product_id:
            item["quantity"] = quantity
            break

    session_save_cart(cart)

    return jsonify({
        "success": True
    })

# ==========================================
# 💳 CHECKOUT
# ==========================================

@app.route("/checkout")
@login_required
def checkout_page():

    return render_template("checkout.html")


# ==========================================
# 💳 CHECKOUT API
# ==========================================

@app.route("/api/checkout", methods=["POST"])
@login_required
def api_checkout():

    data = request.get_json() or {}

    # ==========================================
    # 📌 بيانات العميل
    # ==========================================

    name = data.get("name", "").strip()

    address = data.get(
        "address",
        ""
    ).strip()

    city = data.get(
        "city",
        ""
    ).strip()

    district = data.get(
        "district",
        ""
    ).strip()

    phone = data.get(
        "phone",
        ""
    ).strip()

    # ==========================================
    # ❌ التحقق من البيانات
    # ==========================================

    if not name:
        return jsonify({
            "success": False,
            "error": "Please enter your name."
        }), 400

    if not address:
        return jsonify({
            "success": False,
            "error": "Please enter your delivery address."
        }), 400

    # ==========================================
    # 👤 المستخدم الحالي
    # ==========================================

    user_id = current_user.id

    # ==========================================
    # 📧 البريد الإلكتروني
    # ==========================================

    customer_email = (
        current_user.email or ""
    )

    # ==========================================
    # 🛒 تجهيز السلة
    # ==========================================

    db_cart = get_db_cart_items(user_id)

    cart_entries = []

    products_total = 0

    # ==========================================
    # 🛍️ قراءة المنتجات من السلة
    # ==========================================

    for item in db_cart:

        product = Product.query.get(
            item.product_id
        )

        if not product:
            continue

        # ==========================================
        # 🔢 الكمية
        # ==========================================

        try:
            quantity = int(
                item.quantity
            )
        except (TypeError, ValueError):
            quantity = 0

        if quantity <= 0:
            continue

        # ==========================================
        # 📏 الحجم المختار
        # ==========================================

        selected_size = (
            item.selected_size
            if item.selected_size
            else None
        )

        # ==========================================
        # 💰 السعر المختار
        # ==========================================

        if item.selected_price is not None:

            try:
                item_price = float(
                    item.selected_price
                )

            except (TypeError, ValueError):

                try:
                    item_price = float(
                        product.price
                    )
                except (TypeError, ValueError):
                    item_price = 0

        else:

            try:
                item_price = float(
                    product.price
                )

            except (TypeError, ValueError):
                item_price = 0

        # ==========================================
        # 🎨 التخصيص
        # ==========================================

        customization = None

        if hasattr(
            item,
            "customization"
        ):

            customization = (
                item.customization
            )

        # ==========================================
        # 🧮 إجمالي المنتج
        # ==========================================

        item_total = (
            item_price * quantity
        )

        products_total += item_total

        # ==========================================
        # 📦 حفظ بيانات المنتج
        # ==========================================

        cart_entries.append({

            "product": product,

            "quantity": quantity,

            "item_price": item_price,

            "selected_size": selected_size,

            "customization": customization,

            "item_total": item_total

        })

    # ==========================================
    # 🧺 السلة فارغة
    # ==========================================

    if not cart_entries:

        return jsonify({
            "success": False,
            "error": "Cart is empty."
        }), 400

    # ==========================================
    # 🚚 الشحن
    # ==========================================

    try:

        shipping_cost = float(
            data.get(
                "shipping_cost",
                20
            ) or 20
        )

    except (TypeError, ValueError):

        shipping_cost = 20

    shipping_method = (
        data.get(
            "shipping_method",
            "Standard Shipping"
        )
        or "Standard Shipping"
    )

    # ==========================================
    # 🎁 الكوبون والخصم
    # ==========================================

    try:

        discount = float(
            data.get(
                "discount",
                0
            ) or 0
        )

    except (TypeError, ValueError):

        discount = 0

    coupon_code = (
        data.get(
            "coupon_code",
            ""
        )
        .strip()
        .upper()
    )

    # ==========================================
    # ➕ الإضافات
    # ==========================================

    try:

        extras_total = float(
            data.get(
                "extras_total",
                0
            ) or 0
        )

    except (TypeError, ValueError):

        extras_total = 0

    # ==========================================
    # 🛡️ منع القيم السالبة
    # ==========================================

    shipping_cost = max(
        shipping_cost,
        0
    )

    discount = max(
        discount,
        0
    )

    extras_total = max(
        extras_total,
        0
    )

    # ==========================================
    # 💰 حساب الإجمالي
    # ==========================================

    total = (
        products_total
        + extras_total
        + shipping_cost
        - discount
    )

    # منع الإجمالي من أن يكون سالب
    total = max(
        total,
        0
    )

    # ==========================================
    # 📦 إنشاء الطلب
    # ==========================================

    order = Order(

        user_id=user_id,

        customer_name=name,

        customer_email=customer_email,

        customer_phone=phone,

        address=address,

        city=city,

        district=district,

        payment_method="",

        products_total=products_total,

        extras_total=extras_total,

        shipping_cost=shipping_cost,

        discount=discount,

        coupon_code=(
            coupon_code
            or None
        ),

        total=total,

        shipping_method=shipping_method,

        status="Pending Review"

    )

    db.session.add(
        order
    )

    # ==========================================
    # 🆔 الحصول على Order ID
    # ==========================================

    db.session.flush()

    # ==========================================
    # 🛍️ إضافة المنتجات للطلب
    # ==========================================

    for entry in cart_entries:

        product = entry["product"]

        quantity = entry["quantity"]

        item_price = entry["item_price"]

        selected_size = (
            entry["selected_size"]
        )

        customization = (
            entry["customization"]
        )

        # ==========================================
        # 📦 إنشاء Order Item
        # ==========================================

        order_item = OrderItem(

            order_id=order.id,

            product_id=product.id,

            quantity=quantity,

            price=item_price,

            selected_size=selected_size

        )

        # ==========================================
        # 🎨 حفظ بيانات التخصيص
        # ==========================================

        if hasattr(
            order_item,
            "customization"
        ):

            order_item.customization = (
                customization
            )

        # ==========================================
        # 💾 إضافة المنتج للطلب
        # ==========================================

        db.session.add(
            order_item
        )

    # ==========================================
    # 🗑️ تفريغ السلة
    # ==========================================

    Cart.query.filter_by(
        user_id=user_id
    ).delete()

    # ==========================================
    # 🔔 إشعار الأدمن
    # ==========================================

    notification = Notification(

        message=(
            f"🛍️ طلب جديد رقم #{order.id} "
            f"من العميل "
            f"{order.customer_name}"
        )

    )

    db.session.add(
        notification
    )

    # ==========================================
    # 💾 حفظ كل التغييرات
    # ==========================================

    try:

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print(
            "❌ CHECKOUT ERROR:",
            str(e)
        )

        return jsonify({

            "success": False,

            "error":
                "Failed to create order."

        }), 500

    # ==========================================
    # ✅ النتيجة
    # ==========================================

    return jsonify({

        "success": True,

        "message":
            "Order created successfully",

        "order_id":
            order.id,

        "address":
            order.address,

        "total":
            order.total

    }), 200
# ==================================================
# 🎟️ APPLY COUPON
# ==================================================

@app.route("/api/coupon/validate", methods=["POST"])
def validate_coupon():

    # ==============================================
    # GET DATA
    # ==============================================

    data = request.get_json() or {}

    coupon_code = (
        data.get("code", "")
        .strip()
        .upper()
    )

    order_amount = data.get(
        "order_amount",
        0
    )


    # ==============================================
    # CHECK COUPON CODE
    # ==============================================

    if not coupon_code:

        return jsonify({

            "success": False,

            "error":
                "يرجى إدخال كود الكوبون."

        }), 400


    # ==============================================
    # CHECK ORDER AMOUNT
    # ==============================================

    try:

        order_amount = float(
            order_amount
        )

    except (TypeError, ValueError):

        order_amount = 0


    if order_amount < 0:

        order_amount = 0


    # ==============================================
    # FIND COUPON
    # ==============================================

    coupon = Coupon.query.filter_by(
        code=coupon_code
    ).first()


    # ==============================================
    # COUPON NOT FOUND
    # ==============================================

    if not coupon:

        return jsonify({

            "success": False,

            "error":
                "الكوبون غير صحيح أو منتهي."

        }), 404


    # ==============================================
    # CHECK VALIDITY
    # ==============================================

    if not coupon.is_valid(
        order_amount
    ):

        # ------------------------------------------
        # تحديد سبب عدم صلاحية الكوبون
        # ------------------------------------------

        now = datetime.utcnow()


        if not coupon.is_active:

            error_message = (
                "هذا الكوبون غير مفعل."
            )


        elif (
            order_amount <
            (coupon.minimum_order or 0)
        ):

            minimum = (
                coupon.minimum_order or 0
            )

            error_message = (
                f"الحد الأدنى للطلب "
                f"لاستخدام هذا الكوبون هو "
                f"{minimum:.2f} ر.س."
            )


        elif (
            coupon.start_date
            and now < coupon.start_date
        ):

            error_message = (
                "هذا الكوبون لم يبدأ بعد."
            )


        elif (
            coupon.expiry_date
            and now > coupon.expiry_date
        ):

            error_message = (
                "هذا الكوبون منتهي."
            )


        elif (
            coupon.usage_limit is not None
            and coupon.used_count >= coupon.usage_limit
        ):

            error_message = (
                "تم الوصول إلى الحد الأقصى "
                "لاستخدام هذا الكوبون."
            )


        else:

            error_message = (
                "الكوبون غير صحيح أو منتهي."
            )


        return jsonify({

            "success": False,

            "error":
                error_message

        }), 400


    # ==============================================
    # CALCULATE DISCOUNT
    # ==============================================

    discount = coupon.calculate_discount(
        order_amount
    )


    # ==============================================
    # RETURN RESULT
    # ==============================================

    return jsonify({

        "success": True,

        "coupon_code":
            coupon.code,

        "discount":
            round(discount, 2),

        "discount_type":
            coupon.discount_type,

        "discount_value":
            coupon.discount_value,

        "order_amount":
            round(order_amount, 2),

        "message":
            "تم تطبيق الكوبون بنجاح."

    }), 200


@app.route("/admin/orders/delete", methods=["POST"])
@login_required
def delete_orders():

    if current_user.role != "admin":
        return jsonify({
            "success": False,
            "error": "Access denied."
        }), 403

    data = request.get_json() or {}

    order_ids = data.get("order_ids", [])

    if not order_ids:
        return jsonify({
            "success": False,
            "error": "No orders selected."
        })

    try:

        for order_id in order_ids:

            # حذف منتجات الطلب أولاً
            OrderItem.query.filter_by(
                order_id=order_id
            ).delete()

            # حذف الطلب
            Order.query.filter_by(
                id=order_id
            ).delete()

        db.session.commit()

        return jsonify({
            "success": True
        })

    except Exception as e:

        db.session.rollback()

        print("Delete Orders Error:", e)

        return jsonify({
            "success": False,
            "error": str(e)
        })

# ==========================================
# 👑 ADMIN
# ==========================================

@app.route("/admin")
@login_required
def admin_dashboard():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    return render_template(
        "admin/admin_dashboard.html",
        products=Product.query.all(),
        orders=Order.query.all()
    )


# ==========================================
# 👑 ADMIN HOME
# ==========================================

# =========================================================
# 🏠 ADMIN HOME
# =========================================================


@app.route("/admin/home")
@login_required
def admin_home():

    from datetime import datetime, timedelta

    # -----------------------------------------------------
    # التأكد أن المستخدم Admin
    # -----------------------------------------------------

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # -----------------------------------------------------
    # عدد المستخدمين المسجلين
    # -----------------------------------------------------

    user_count = User.query.count()

    # -----------------------------------------------------
    # الوقت الحالي بتوقيت UTC
    # Railway / السيرفر يستخدم UTC
    # -----------------------------------------------------

    utc_now = datetime.utcnow()

    # -----------------------------------------------------
    # تحويل الوقت إلى توقيت السعودية
    # السعودية = UTC + 3
    # -----------------------------------------------------

    saudi_now = utc_now + timedelta(hours=3)

    # -----------------------------------------------------
    # بداية اليوم في السعودية
    # -----------------------------------------------------

    saudi_today_start = saudi_now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # -----------------------------------------------------
    # تحويل بداية اليوم السعودي إلى UTC
    # حتى نقارنها مع started_at في قاعدة البيانات
    # -----------------------------------------------------

    today_start = saudi_today_start - timedelta(hours=3)

    # -----------------------------------------------------
    # زيارات اليوم فقط
    # -----------------------------------------------------

    today_visitor_count = Visitor.query.filter(
        Visitor.started_at >= today_start
    ).count()

    # -----------------------------------------------------
    # الزوار المسجلين اليوم
    # -----------------------------------------------------

    today_registered_count = Visitor.query.filter(
        Visitor.started_at >= today_start,
        Visitor.visitor_type == "registered"
    ).count()

    # -----------------------------------------------------
    # الزوار غير المسجلين اليوم
    # -----------------------------------------------------

    today_guest_count = Visitor.query.filter(
        Visitor.started_at >= today_start,
        Visitor.visitor_type == "guest"
    ).count()

    # -----------------------------------------------------
    # الصفحة
    # -----------------------------------------------------

    return render_template(
        "admin/admin_home.html",

        user_count=user_count,

        # كرت الزوار في الصفحة الرئيسية
        # يعرض زيارات اليوم فقط
        visitor_count=today_visitor_count,

        # هذه متاحة للصفحة إذا احتجناها لاحقًا
        today_visitor_count=today_visitor_count,
        today_registered_count=today_registered_count,
        today_guest_count=today_guest_count
    )

# =========================================================
# 👀 ADMIN VISITORS
# =========================================================

@app.route("/admin/visitors")
@login_required
def admin_visitors():

    from datetime import datetime, timedelta

    # =====================================================
    # 🔐 ADMIN CHECK
    # =====================================================

    if current_user.role != "admin":
        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )
        return redirect(
            url_for("home_logged")
        )

    # =====================================================
    # 🕐 CURRENT TIME
    # =====================================================

    now = datetime.now()

    # =====================================================
    # 📅 TODAY
    # =====================================================

    today_start = datetime(
        now.year,
        now.month,
        now.day
    )

    tomorrow_start = today_start + timedelta(days=1)

    # =====================================================
    # 📅 THIS WEEK
    # =====================================================

    week_start = (
        today_start
        - timedelta(
            days=today_start.weekday()
        )
    )

    next_week_start = (
        week_start
        + timedelta(days=7)
    )

    # =====================================================
    # 📅 THIS MONTH
    # =====================================================

    month_start = datetime(
        now.year,
        now.month,
        1
    )

    # بداية الشهر القادم
    if now.month == 12:

        next_month_start = datetime(
            now.year + 1,
            1,
            1
        )

    else:

        next_month_start = datetime(
            now.year,
            now.month + 1,
            1
        )

    # =====================================================
    # 👀 GET ALL VISITORS
    # =====================================================

    visitors = (
        Visitor.query
        .order_by(
            Visitor.visited_at.desc()
        )
        .all()
    )

    # =====================================================
    # 📊 TOTAL VISITS
    # =====================================================

    visitor_count = len(visitors)

    total_visitors = visitor_count

    # =====================================================
    # 📅 TODAY VISITS
    # =====================================================

    today_visitors = sum(
        1
        for visitor in visitors
        if (
            visitor.visited_at
            and
            today_start
            <= visitor.visited_at
            < tomorrow_start
        )
    )

    # =====================================================
    # 👤 REGISTERED VISITORS
    # =====================================================

    registered_visitors = sum(
        1
        for visitor in visitors
        if visitor.user_id
    )

    # =====================================================
    # 👀 GUEST VISITORS
    # =====================================================

    guest_visitors = sum(
        1
        for visitor in visitors
        if not visitor.user_id
    )

    # =====================================================
    # 🟢 ACTIVE VISITORS
    #
    # الزائر يعتبر "الآن" إذا كان آخر نشاط له
    # خلال آخر 30 دقيقة.
    # =====================================================

    active_visitors = [
        visitor
        for visitor in visitors
        if (
            visitor.last_activity
            and
            (
                now - visitor.last_activity
            ).total_seconds()
            <= 1800
        )
    ]

    # =====================================================
    # 🟢 ACTIVE COUNT
    # =====================================================

    active_count = len(
        active_visitors
    )

    # =====================================================
    # 👤 REGISTERED NOW
    # =====================================================

    active_registered = sum(
        1
        for visitor in active_visitors
        if visitor.user_id
    )

    # =====================================================
    # 👀 GUESTS NOW
    # =====================================================

    active_guests = sum(
        1
        for visitor in active_visitors
        if not visitor.user_id
    )

    # =====================================================
    # 📅 REGISTERED TODAY
    # =====================================================

    today_registered_count = sum(
        1
        for visitor in visitors
        if (
            visitor.user_id
            and
            visitor.visited_at
            and
            today_start
            <= visitor.visited_at
            < tomorrow_start
        )
    )

    # =====================================================
    # 📅 GUESTS TODAY
    # =====================================================

    today_guest_count = sum(
        1
        for visitor in visitors
        if (
            not visitor.user_id
            and
            visitor.visited_at
            and
            today_start
            <= visitor.visited_at
            < tomorrow_start
        )
    )

    # =====================================================
    # 📅 WEEK VISITS
    # =====================================================

    week_visitors = sum(
        1
        for visitor in visitors
        if (
            visitor.visited_at
            and
            week_start
            <= visitor.visited_at
            < next_week_start
        )
    )

    # =====================================================
    # 📅 MONTH VISITS
    # =====================================================

    month_visitors = sum(
        1
        for visitor in visitors
        if (
            visitor.visited_at
            and
            month_start
            <= visitor.visited_at
            < next_month_start
        )
    )

    # =====================================================
    # 👤 GET USER DATA
    # =====================================================

    visitor_user_ids = {
        visitor.user_id
        for visitor in visitors
        if visitor.user_id
    }

    visitor_users = {}

    if visitor_user_ids:

        users = (
            User.query
            .filter(
                User.id.in_(
                    visitor_user_ids
                )
            )
            .all()
        )

        visitor_users = {
            user.id: user
            for user in users
        }

    # =====================================================
    # 🖥️ RENDER PAGE
    # =====================================================

    return render_template(
        "admin/admin_visitors.html",

        # -------------------------------------------------
        # Visitors
        # -------------------------------------------------

        visitors=visitors,

        # -------------------------------------------------
        # Users
        # -------------------------------------------------

        visitor_users=visitor_users,

        # -------------------------------------------------
        # Current time
        # -------------------------------------------------

        now=now,

        # -------------------------------------------------
        # Today
        # -------------------------------------------------

        today_start=today_start,
        tomorrow_start=tomorrow_start,

        # -------------------------------------------------
        # Week
        # -------------------------------------------------

        week_start=week_start,
        next_week_start=next_week_start,

        # -------------------------------------------------
        # Month
        # -------------------------------------------------

        month_start=month_start,
        next_month_start=next_month_start,

        # -------------------------------------------------
        # Main statistics
        # -------------------------------------------------

        visitor_count=visitor_count,
        total_visitors=total_visitors,

        today_visitors=today_visitors,

        registered_visitors=registered_visitors,

        guest_visitors=guest_visitors,

        # -------------------------------------------------
        # Active statistics
        # -------------------------------------------------

        active_count=active_count,

        active_registered=active_registered,

        active_guests=active_guests,

        # -------------------------------------------------
        # Today statistics
        # -------------------------------------------------

        today_registered_count=(
            today_registered_count
        ),

        today_guest_count=(
            today_guest_count
        ),

        # -------------------------------------------------
        # Period statistics
        # -------------------------------------------------

        week_visitors=week_visitors,

        month_visitors=month_visitors
    )

# =========================================================
# 🧹 CLEAR VISITOR LOG
# =========================================================

@app.route("/admin/visitors/clear", methods=["POST"])
@login_required
def clear_visitor_log():

    # =====================================================
    # 🔐 ADMIN CHECK
    # =====================================================

    if current_user.role != "admin":
        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )
        return redirect(
            url_for("home_logged")
        )

    try:
        # =================================================
        # 🗑️ DELETE ALL VISITOR RECORDS
        # =================================================

        Visitor.query.delete(
            synchronize_session=False
        )

        db.session.commit()

        # =================================================
        # ✅ SUCCESS
        # =================================================

        flash(
            "تم تنظيف سجل الزوار بنجاح.",
            "success"
        )

    except Exception as e:

        # =================================================
        # ❌ ERROR
        # =================================================

        db.session.rollback()

        print(
            f"❌ ERROR CLEARING VISITOR LOG: {e}"
        )

        flash(
            "حدث خطأ أثناء تنظيف سجل الزوار.",
            "danger"
        )

    return redirect(
        url_for("admin_visitors")
    )
# ==========================================
# 📦 ADMIN ORDERS
# ==========================================

@app.route("/admin/orders")
@login_required
def admin_orders():

    # السماح للأدمن فقط
    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # ======================================
    # جعل إشعارات الطلبات مقروءة
    # ======================================
    Notification.query.filter_by(
        is_read=False
    ).update({
        Notification.is_read: True
    })

    db.session.commit()

    # ======================================
    # فلترة الطلبات
    # ======================================
    status = request.args.get("status", "all")

    query = Order.query.order_by(Order.id.desc())

    if status != "all":
        query = query.filter_by(status=status)

    orders = query.all()

    # ======================================
    # عداد الحالات
    # ======================================
    counts = {
        "all": Order.query.count(),
        "Pending Payment": Order.query.filter_by(status="Pending Payment").count(),
        "Pending Review": Order.query.filter_by(status="Pending Review").count(),
        "Processing": Order.query.filter_by(status="Processing").count(),
        "Completed": Order.query.filter_by(status="Completed").count(),
        "Shipping": Order.query.filter_by(status="Shipping").count(),
        "Delivered": Order.query.filter_by(status="Delivered").count(),
        "Cancelled": Order.query.filter_by(status="Cancelled").count(),
    }

    return render_template(
        "admin/admin_orders.html",
        orders=orders,
        counts=counts,
        current_status=status
    )
# ==================================================
# 🎟️ ADMIN COUPONS
# ==================================================

@app.route("/admin/coupons")
@login_required
def admin_coupons():

    # التأكد أن المستخدم أدمن
    if current_user.role != "admin":

        flash(
            "غير مسموح لك بالدخول إلى هذه الصفحة."
            if session.get("lang", "ar") == "ar"
            else "You are not authorized to access this page.",
            "error"
        )

        return redirect(url_for("home_logged"))

    coupons = Coupon.query.order_by(
        Coupon.created_at.desc()
    ).all()

    return render_template(
        "admin/coupons.html",
        coupons=coupons
    )
@app.context_processor
def inject_admin_notifications():

    unread_notifications = Notification.query.filter_by(
        is_read=False
    ).count()

    return dict(
        unread_notifications=unread_notifications
    )
# ==================================================
# 🎟️ ADD COUPON PAGE + CREATE COUPON
# ==================================================

# ==================================================
# 🎟️ ADD COUPON
# ==================================================

@app.route("/admin/coupons/add", methods=["POST"])
@login_required
def add_coupon():

    # ==========================================
    # 🌐 اللغة الحالية
    # ==========================================

    current_lang = session.get(
        "lang",
        "ar"
    )

    # ==========================================
    # 📋 بيانات النموذج
    # ==========================================

    code = request.form.get(
        "code",
        ""
    ).strip().upper()

    discount_type = request.form.get(
        "discount_type",
        "percentage"
    ).strip()

    discount_value = request.form.get(
        "discount_value",
        "0"
    ).strip()

    minimum_order = request.form.get(
        "minimum_order",
        "0"
    ).strip()

    maximum_discount = request.form.get(
        "maximum_discount",
        ""
    ).strip()

    usage_limit = request.form.get(
        "usage_limit",
        ""
    ).strip()

    # ==========================================
    # 🔎 التحقق من الكود
    # ==========================================

    if not code:

        flash(
            "يرجى إدخال كود الكوبون."
            if current_lang == "ar"
            else "Please enter a coupon code.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 🔎 التحقق من نوع الخصم
    # ==========================================

    if discount_type not in [
        "percentage",
        "fixed"
    ]:

        flash(
            "نوع الخصم غير صحيح."
            if current_lang == "ar"
            else "Invalid discount type.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 🚫 منع تكرار الكوبون
    # ==========================================

    existing_coupon = Coupon.query.filter_by(
        code=code
    ).first()

    if existing_coupon:

        flash(
            "هذا الكوبون موجود بالفعل."
            if current_lang == "ar"
            else "This coupon already exists.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 🔢 تحويل القيم إلى أرقام
    # ==========================================

    try:

        discount_value = float(
            discount_value
        )

        minimum_order = float(
            minimum_order or 0
        )

        maximum_discount = (
            float(maximum_discount)
            if maximum_discount
            else None
        )

        usage_limit = (
            int(usage_limit)
            if usage_limit
            else None
        )

    except ValueError:

        flash(
            "يرجى إدخال أرقام صحيحة."
            if current_lang == "ar"
            else "Please enter valid numbers.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 💰 التحقق من قيمة الخصم
    # ==========================================

    if discount_value <= 0:

        flash(
            "قيمة الخصم يجب أن تكون أكبر من صفر."
            if current_lang == "ar"
            else "Discount value must be greater than zero.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 🛒 الحد الأدنى للطلب
    # ==========================================

    if minimum_order < 0:

        flash(
            "الحد الأدنى للطلب غير صحيح."
            if current_lang == "ar"
            else "Invalid minimum order.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 📊 التحقق من النسبة المئوية
    # ==========================================

    if discount_type == "percentage":

        if discount_value > 100:

            flash(
                "نسبة الخصم لا يمكن أن تتجاوز 100٪."
                if current_lang == "ar"
                else "Percentage discount cannot exceed 100%.",
                "error"
            )

            return redirect(
                url_for("admin_coupons")
            )

        if (
            maximum_discount is not None
            and maximum_discount <= 0
        ):

            flash(
                "الحد الأقصى للخصم يجب أن يكون أكبر من صفر."
                if current_lang == "ar"
                else "Maximum discount must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("admin_coupons")
            )

    # ==========================================
    # 💵 الخصم الثابت
    # ==========================================

    if discount_type == "fixed":

        maximum_discount = None

    # ==========================================
    # 🔢 حد الاستخدام
    # ==========================================

    if (
        usage_limit is not None
        and usage_limit <= 0
    ):

        flash(
            "عدد مرات الاستخدام يجب أن يكون أكبر من صفر."
            if current_lang == "ar"
            else "Usage limit must be greater than zero.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # 🎟️ إنشاء الكوبون
    # ==========================================

    coupon = Coupon(

        code=code,

        discount_type=discount_type,

        discount_value=discount_value,

        minimum_order=minimum_order,

        maximum_discount=maximum_discount,

        usage_limit=usage_limit,

        used_count=0,

        is_active=True

    )

    # ==========================================
    # 💾 حفظ الكوبون
    # ==========================================

    try:

        db.session.add(
            coupon
        )

        db.session.commit()

    except Exception as e:

        db.session.rollback()

        print(
            "Add Coupon Error:",
            e
        )

        flash(
            "حدث خطأ أثناء إنشاء الكوبون."
            if current_lang == "ar"
            else "An error occurred while creating the coupon.",
            "error"
        )

        return redirect(
            url_for("admin_coupons")
        )

    # ==========================================
    # ✅ نجاح
    # ==========================================

    flash(
        "تم إنشاء الكوبون بنجاح 🎉"
        if current_lang == "ar"
        else "Coupon created successfully 🎉",
        "success"
    )

    return redirect(
        url_for("admin_coupons")
    )
# ==========================================
# 📦 UPDATE ORDER STATUS
# ==========================================

@app.route("/admin/orders/update-status", methods=["POST"])
@login_required
def update_order_status():

    if not session.get("is_admin"):
        return jsonify({"success": False}), 403

    data = request.get_json()

    order_ids = data.get("order_ids", [])
    status = data.get("status")

    if not order_ids or not status:
        return jsonify({
            "success": False,
            "message": "Missing data."
        }), 400

    orders = Order.query.filter(
        Order.id.in_(order_ids)
    ).all()

    for order in orders:
        order.status = status

    db.session.commit()

    return jsonify({
        "success": True
    })


@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):

    order = Order.query.get_or_404(order_id)

    return render_template(
        "admin/order_detail.html",
        order=order
    )

@app.route("/admin/orders/<int:order_id>/update", methods=["POST"])
def update_order_detail(order_id):

    order = Order.query.get_or_404(order_id)

    order.status = request.form.get("status")
    order.tracking_number = request.form.get("tracking_number")
    order.shipping_company = request.form.get("shipping_company")

    db.session.commit()

    return redirect(
        url_for(
            "admin_order_detail",
            order_id=order.id
        )
    )

# ==========================================
# 🧾 PRINT INVOICE
# ==========================================

@app.route("/admin/invoice/<int:order_id>")
@login_required
def admin_invoice(order_id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    order = Order.query.get_or_404(order_id)

    return render_template(
        "admin/invoice.html",
        order=order
    )
# ==========================================
# 🛍 PRODUCTS PAGE
# ==========================================

@app.route("/products")
def products_page():

    products = Product.query.filter(
        Product.publish_location.in_(
            ["both", "products_only"]
        )
    ).all()

    wishlist_ids = []

    if current_user.is_authenticated:

        wishlist_ids = [
            item.product_id
            for item in current_user.wishlist_items
        ]

    return render_template(
        "products.html",
        products=products,
        wishlist_ids=wishlist_ids
    )












































# ==========================================
# 🧶 PRODUCTS MANAGEMENT
# ==========================================

@app.route("/admin/products")
@login_required
def admin_products():

    # ==================================================
    # 🔐 ADMIN CHECK
    # ==================================================

    if current_user.role != "admin":

        flash(
            "⚠️ Access denied! Admins only.",
            "danger"
        )

        return redirect(
            url_for("home_logged")
        )


    # ==================================================
    # 📦 GET PRODUCTS
    # ==================================================

    products = Product.query.order_by(
        Product.id.desc()
    ).all()


    # ==================================================
    # 📝 FORM
    # ProductForm يحتوي على الحقول التي تستخدمها الصفحة
    # ومنها is_customizable
    # ==================================================

    form = ProductForm()


    # ==================================================
    # 🖥️ PRODUCTS PAGE
    # ==================================================

    return render_template(
        "admin/add_product.html",
        products=products,
        form=form
    )

# ==========================================
# 👥 USER MANAGEMENT
# ==========================================

@app.route('/admin/users')
@login_required
def admin_users():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    search = request.args.get("search", "").strip()

    users_query = User.query

    if search:
        users_query = users_query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    users = users_query.order_by(
        User.id.desc()
    ).all()

    users_count = User.query.count()

    return render_template(
        "admin/admin_users.html",
        users=users,
        users_count=users_count,
        search=search
    )


# ==========================================
# 🗑️ DELETE USER
# ==========================================

@app.route('/admin/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):

    # التأكد أن المستخدم أدمن
    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # جلب المستخدم
    user = User.query.get_or_404(id)

    # حماية الأدمن الرئيسي
    if user.email == "admin@store.com":
        flash(
            "⚠️ لا يمكنك حذف حساب الأدمن الرئيسي.",
            "warning"
        )
        return redirect(url_for("admin_users"))

    # منع الأدمن من حذف نفسه
    if user.id == current_user.id:
        flash(
            "⚠️ لا يمكنك حذف حسابك الحالي.",
            "warning"
        )
        return redirect(url_for("admin_users"))

    try:
        username = user.username

        # ==========================================
        # 🗑️ حذف سجلات الزيارات المرتبطة بالمستخدم أولاً
        # ==========================================
        Visitor.query.filter_by(
            user_id=user.id
        ).delete(
            synchronize_session=False
        )

        # ==========================================
        # 🗑️ حذف المستخدم
        # ==========================================
        db.session.delete(user)

        # حفظ التغييرات
        db.session.commit()

        flash(
            f"🗑️ تم حذف المستخدم {username} بنجاح.",
            "success"
        )

    except Exception as e:

        # إذا صار خطأ نلغي العملية
        db.session.rollback()

        print("❌ DELETE USER ERROR:", str(e))

        flash(
            "❌ حدث خطأ أثناء حذف المستخدم.",
            "danger"
        )

    return redirect(url_for("admin_users"))
# ==========================================
# 🔑 RESET USER PASSWORD
# ==========================================

@app.route('/admin/change_user_password/<int:id>', methods=['POST'])
@login_required
def change_user_password(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    user = User.query.get_or_404(id)

    new_password = request.form.get(
        "new_password",
        ""
    ).strip()

    if not new_password:
        flash(
            "❌ يجب إدخال كلمة المرور الجديدة.",
            "danger"
        )
        return redirect(url_for("admin_users"))

    if len(new_password) < 6:
        flash(
            "❌ كلمة المرور يجب أن تكون 6 أحرف على الأقل.",
            "danger"
        )
        return redirect(url_for("admin_users"))

    user.set_password(new_password)

    db.session.commit()

    flash(
        f"🔑 تم تغيير كلمة مرور {user.username} بنجاح.",
        "success"
    )

    return redirect(url_for("admin_users"))
# ==========================================
# 📩 CONTACT
# ==========================================

# ==================================================
# 💌 CONTACT PAGE
# ==================================================

@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact_page():

    # ==================================================
    # 🌐 LANGUAGE
    # ==================================================
    current_lang = session.get("language", "ar")

    # ==================================================
    # 📩 SEND MESSAGE
    # ==================================================
    if request.method == "POST":

        message_text = request.form.get("message")

        # التأكد أن الرسالة ليست فارغة
        if not message_text or not message_text.strip():
            flash(
                "الرجاء كتابة رسالة."
                if current_lang == "ar"
                else "Please write a message."
            )
            return redirect(url_for("contact_page"))

        # إنشاء الرسالة
        new_message = Message(
            user_id=current_user.id,
            name=current_user.username,
            email=current_user.email,
            message=message_text.strip(),
            sender="customer",
            is_read=False
        )

        db.session.add(new_message)
        db.session.commit()

        flash(
            "💖 تم إرسال رسالتك بنجاح!"
            if current_lang == "ar"
            else "💖 Your message has been sent successfully!"
        )

        return redirect(url_for("contact_page"))

    # ==================================================
    # 💬 GET CUSTOMER CONVERSATION
    # ==================================================
    messages = (
        Message.query
        .filter_by(user_id=current_user.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    # ==================================================
    # 📄 RENDER CONTACT PAGE
    # ==================================================
    return render_template(
        "contact.html",
        messages=messages
    )
# ==========================================
# 📨 ADMIN MESSAGES
# ==========================================

# ==================================================
# 💌 ADMIN MESSAGES
# ==================================================

@app.route('/admin/messages')
@login_required
def admin_messages():

    # =====================================================
    # 🔐 ADMIN CHECK
    # =====================================================

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # =====================================================
    # 💬 جلب جميع الرسائل
    # =====================================================

    all_messages = (
        Message.query
        .order_by(Message.created_at.asc())
        .all()
    )

    # =====================================================
    # 👥 تجميع الرسائل حسب العميل
    # =====================================================

    conversations_dict = {}

    for msg in all_messages:

        # نتجاهل أي رسالة بدون user_id
        if not msg.user_id:
            continue

        user_id = msg.user_id

        # إنشاء محادثة جديدة للعميل
        if user_id not in conversations_dict:

            conversations_dict[user_id] = {
                "user_id": user_id,
                "name": msg.name or "Customer",
                "email": msg.email or "",
                "messages": [],
                "unread": False
            }

        # إضافة الرسالة للمحادثة
        conversations_dict[user_id]["messages"].append(msg)

        # =================================================
        # 🔴 تحديد وجود رسائل غير مقروءة
        # =================================================

        if msg.sender != "admin" and not msg.is_read:
            conversations_dict[user_id]["unread"] = True

    # =====================================================
    # 📋 تحويل Dictionary إلى List
    # =====================================================

    conversations = list(conversations_dict.values())

    # =====================================================
    # 🕐 ترتيب المحادثات حسب آخر رسالة
    # =====================================================

    conversations.sort(
        key=lambda conversation: (
            conversation["messages"][-1].created_at
            if conversation["messages"]
            and conversation["messages"][-1].created_at
            else datetime.min
        ),
        reverse=True
    )

    # =====================================================
    # 📄 عرض صفحة الأدمن
    # =====================================================

    return render_template(
        "admin/admin_messages.html",
        conversations=conversations
    )

# ==================================================
# 💬 ADMIN REPLY TO CUSTOMER
# ==================================================

@app.route('/admin/messages/reply/<int:user_id>', methods=['POST'])
@login_required
def admin_reply_message(user_id):

    # 🔐 ADMIN CHECK
    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # =====================================================
    # 📝 الحصول على الرسالة
    # =====================================================

    message_text = request.form.get("message", "").strip()

    # =====================================================
    # ❌ التأكد أن الرسالة ليست فارغة
    # =====================================================

    if not message_text:
        flash("⚠️ Please write a reply.", "danger")
        return redirect(url_for("admin_messages"))

    # =====================================================
    # 👤 البحث عن العميل
    # =====================================================

    customer = User.query.get(user_id)

    if not customer:
        flash("⚠️ Customer not found.", "danger")
        return redirect(url_for("admin_messages"))

    # =====================================================
    # 💬 إنشاء رسالة الأدمن
    # =====================================================

    new_message = Message(
        user_id=customer.id,
        name=customer.username,
        email=customer.email,
        message=message_text,
        sender="admin",
        is_read=True
    )

    db.session.add(new_message)
    db.session.commit()

    flash("💗 Reply sent successfully!", "success")

    return redirect(url_for("admin_messages"))
# ==================================================
# 🗑️ DELETE CUSTOMER CONVERSATION
# ==================================================

@app.route(
    "/admin/messages/delete_customer/<int:user_id>",
    methods=["POST"]
)
@login_required
def admin_delete_customer_messages(user_id):

    # 🔐 ADMIN CHECK
    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    try:

        # 🗑️ Delete ALL messages belonging to this customer
        Message.query.filter_by(
            user_id=user_id
        ).delete(
            synchronize_session=False
        )

        db.session.commit()

        flash(
            "🗑️ تم حذف المحادثة كاملة بنجاح.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            "❌ DELETE CUSTOMER CONVERSATION ERROR:",
            str(e)
        )

        flash(
            "❌ حدث خطأ أثناء حذف المحادثة.",
            "danger"
        )

    return redirect(
        url_for("admin_messages")
    )
@app.route('/admin/messages/delete/<int:message_id>', methods=['POST'])
@login_required
def admin_delete_message(message_id):

    # 🔐 ADMIN CHECK
    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # =====================================================
    # 🔎 البحث عن الرسالة
    # =====================================================

    message = Message.query.get(message_id)

    if not message:
        flash("⚠️ Message not found.", "danger")
        return redirect(url_for("admin_messages"))

    # =====================================================
    # 🚫 منع الأدمن من حذف رسالة أدمن من هذا المسار
    # =====================================================

    if message.sender == "admin":
        flash("⚠️ Admin messages cannot be deleted here.", "danger")
        return redirect(url_for("admin_messages"))

    # =====================================================
    # 🗑 حذف رسالة العميل
    # =====================================================

    db.session.delete(message)
    db.session.commit()

    flash("🗑️ Message deleted successfully.", "success")

    return redirect(url_for("admin_messages"))

@app.route('/admin/messages/delete-conversation/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_conversation(user_id):

    # =====================================================
    # 🔐 ADMIN CHECK
    # =====================================================

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    # =====================================================
    # 👤 التأكد أن العميل موجود
    # =====================================================

    customer = User.query.get(user_id)

    if not customer:
        flash("⚠️ Customer not found.", "danger")
        return redirect(url_for("admin_messages"))

    # =====================================================
    # 💬 حذف جميع رسائل هذا العميل
    # =====================================================

    Message.query.filter_by(
        user_id=user_id
    ).delete(
        synchronize_session=False
    )

    db.session.commit()

    # =====================================================
    # ✅ SUCCESS
    # =====================================================

    flash(
        f"🗑️ Conversation with {customer.username} deleted successfully.",
        "success"
    )

    return redirect(url_for("admin_messages"))
# ==========================================
# 🏠 USER HOME
# ==========================================

# ==========================================
# 🏠 USER HOME
# ==========================================

@app.route("/home_logged")
@login_required
def home_logged():

    if current_user.role == "admin":
        return redirect(url_for("admin_home"))

    products = Product.query.order_by(
        Product.created_at.desc()
    ).all()

    advertisements = Advertisement.query.filter_by(
        is_active=True
    ).order_by(
        Advertisement.display_order.asc(),
        Advertisement.id.asc()
    ).all()

    return render_template(
        "home_logged.html",
        products=products,
        advertisements=advertisements,
        user=current_user.username
    )

# ==========================================
# ⭐ ADMIN REVIEWS
# ==========================================

@app.route("/admin/reviews", methods=["GET", "POST"])
@login_required
def admin_reviews():

    if current_user.role != "admin":
        return redirect(url_for("home_logged"))

    reviews = Review.query.all()

    return render_template(
        "admin/admin_reviews.html",
        reviews=reviews
    )


@app.route("/admin/reviews/delete/<int:id>", methods=["POST"])
@login_required
def delete_review(id):

    if current_user.role != "admin":
        return redirect(url_for("home_logged"))

    review = Review.query.get_or_404(id)

    db.session.delete(review)
    db.session.commit()

    flash("✅ Review deleted successfully.")

    return redirect(url_for("admin_reviews"))


@app.route("/admin/reviews/reply/<int:id>", methods=["POST"])
@login_required
def reply_review(id):

    if current_user.role != "admin":
        return redirect(url_for("home_logged"))

    review = Review.query.get_or_404(id)
    review.admin_reply = request.form["reply"]

    db.session.commit()

    flash("💌 Reply sent successfully!")

    return redirect(url_for("admin_reviews"))


# ==========================================
# 🔑 RESET ADMIN PASSWORD
# ==========================================

@app.route("/reset_admin")
def reset_admin():

    admin = User.query.filter_by(email="admin@store.com").first()

    if not admin:
        return "Admin account not found."

    admin.set_password("12345678")

    db.session.commit()

    return "Password changed successfully."