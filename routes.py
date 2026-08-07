from flask import (
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash
)



from app import app, db, mail

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
    Visitor


)

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

from flask_mail import Message as MailMessage
from app import mail

from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer

from datetime import datetime
import os

import random
from datetime import datetime, timedelta
from flask import jsonify
import random
from sqlalchemy import func
from flask_login import login_user, logout_user, login_required, current_user


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

s = URLSafeTimedSerializer(app.config["SECRET_KEY"])


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
                filename=f"images/{product.image}"
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
    query = request.args.get("q")

    return render_template(
        "products.html",
        query=query
    )


# ==========================================
# 📦 ADD PRODUCT
# ==========================================

@app.route("/admin/add_product", methods=["GET", "POST"])
@login_required
def add_product():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    form = ProductForm()

    if form.validate_on_submit():

        filename = None

        if form.image.data:

            image_file = form.image.data
            filename = secure_filename(image_file.filename)

            image_path = os.path.join(
                app.root_path,
                "static",
                "images",
                filename
            )

            image_file.save(image_path)

        product = Product(
            name=form.name.data,
            price=form.price.data,
            description=form.description.data,
            image=filename,
            publish_location=form.publish_location.data
        )

        db.session.add(product)
        db.session.commit()

        flash("✅ Product added successfully!", "success")

        return redirect(url_for("admin_products"))

    return render_template(
        "admin/add_product.html",
        form=form
    )


# ==========================================
# ✏️ ADD / EDIT PRODUCT (Legacy)
# ==========================================

@app.route("/admin/product", methods=["GET", "POST"])
@app.route("/admin/product/<int:product_id>", methods=["GET", "POST"])
def add_or_edit_product(product_id=None):

    edit_mode = product_id is not None

    product = Product.query.get(product_id) if edit_mode else None

    form = AddProductForm(obj=product)

    if form.validate_on_submit():

        name = form.name.data
        price = form.price.data
        description = form.description.data
        publish_location = form.publish_location.data

        image_file = form.image.data

        filename = (
            product.image
            if edit_mode and product.image
            else None
        )

        if image_file and allowed_file(image_file.filename):

            filename = secure_filename(image_file.filename)

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image_file.save(image_path)

        if edit_mode:

            product.name = name
            product.price = price
            product.description = description
            product.publish_location = publish_location
            product.image = filename

            flash(
                "✅ Product updated successfully!",
                "success"
            )

        else:

            new_product = Product(
                name=name,
                price=price,
                description=description,
                image=filename,
                publish_location=publish_location
            )

            db.session.add(new_product)

            flash(
                "🧶 Product added successfully!",
                "success"
            )

        db.session.commit()

        return redirect(url_for("admin_home"))

    return render_template(
        "add_product.html",
        form=form,
        edit_mode=edit_mode,
        product=product
    )
# ==========================================
# PRODUCT DETAILS
# ==========================================

@app.route("/product/<int:product_id>")
def product_details(product_id):

    product = Product.query.get_or_404(product_id)

    related_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id
    ).limit(4).all()

    return render_template(
        "product_details.html",
        product=product,
        related_products=related_products
    )



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




@app.route("/my-order/<int:order_id>")
@login_required
def customer_order_detail(order_id):

    order = Order.query.filter_by(
        id=order_id,
        user_id=current_user.id
    ).first_or_404()


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

@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():

        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        # التحقق من البريد
        existing_email = User.query.filter(
            func.lower(User.email) == email
        ).first()

        if existing_email:

            flash("⚠️ Email already registered!", "register_warning")

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

        # التحقق من اسم المستخدم
        existing_username = User.query.filter(
            func.lower(User.username) == username.lower()
        ).first()

        if existing_username:

            flash("⚠️ Username already exists!", "register_warning")

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

        code = str(random.randint(100000, 999999))

        new_user = User(
            username=username,
            email=email,
            phone=form.phone.data
        )

        new_user.set_password(form.password.data)

        if email == "admin@store.com":
            new_user.role = "admin"

        new_user.confirmed = False
        new_user.verification_code = code
        new_user.verification_expiry = (
            datetime.utcnow() + timedelta(minutes=10)
        )

        db.session.add(new_user)
        db.session.commit()

        session["verify_email"] = new_user.email

        try:
            msg = MailMessage(
                subject="Verify your Crochet Rory account",
                recipients=[new_user.email]
            )

            msg.body = f"""
Hi {new_user.username},

Welcome to Crochet Rory 💖

Thank you for registering.

Your verification code is:

{code}

This code will expire in 10 minutes.

Please enter this code to activate your account.

Crochet Rory Team
"""

            mail.send(msg)

        except Exception as e:
            print("Mail Error:", e)

        return redirect(url_for("index", verify=1))

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
        verify_form=verify_form
    )
    
@app.route("/forgot_password", methods=["POST"])
def forgot_password():

    email = request.form.get("email")

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("❌ Email not found.", "danger")
        return redirect(url_for("index"))

    code = str(random.randint(100000, 999999))

    user.verification_code = code
    user.verification_expiry = datetime.utcnow() + timedelta(minutes=10)

    db.session.commit()

    try:

        msg = MailMessage(
            subject="Reset your Crochet Rory password",
            recipients=[user.email]
        )

        msg.body = f"""
Hi {user.username},

You requested to reset your password.

Your verification code is:

{code}

This code will expire in 10 minutes.

Crochet Rory Team
"""

        mail.send(msg)

    except Exception as e:
        print("Mail Error:", e)

    session["reset_email"] = user.email

    flash("📧 Verification code sent.", "success")

    return redirect(url_for("index", verify=1))

@app.route("/verify_reset_code", methods=["POST"])
def verify_reset_code():

    code = request.form.get("code")

    email = session.get("reset_email")

    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("index"))

    if datetime.utcnow() > user.verification_expiry:
        flash("❌ Verification code expired.", "danger")
        return redirect(url_for("index"))

    if code != user.verification_code:
        flash("❌ Invalid verification code.", "danger")
        return redirect(url_for("index", verify=1))

    print("✅ Correct reset code")

    return redirect(url_for("index", reset=1))
# ==========================================
# 📧 VERIFY EMAIL
# ==========================================

@app.route("/verify_email", methods=["GET", "POST"])
def verify_email():

    form = VerifyCodeForm()

    email = session.get("verify_email")

    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("index"))

    if form.validate_on_submit():

        # انتهت صلاحية الكود
        if datetime.utcnow() > user.verification_expiry:
            flash("Verification code has expired.", "danger")
            return redirect(url_for("index"))

        # الكود خطأ
        if form.code.data != user.verification_code:
            flash("Invalid verification code.", "danger")
            return redirect(url_for("verify_email"))

        # نجاح التحقق
        user.confirmed = True
        user.verification_code = None
        user.verification_expiry = None

        db.session.commit()

        session.pop("verify_email", None)

        flash("🎉 Your account has been verified successfully!", "success")

        return redirect(url_for("index"))

    login_form = LoginForm()
    register_form = RegisterForm()

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    return render_template(
        "index.html",
        products=products,
        form=login_form,
        register_form=register_form,
        verify_form=form,
        show_verify_popup=True
    )

@app.route("/reset_password", methods=["POST"])
def reset_password():

    email = session.get("reset_email")

    if not email:
        flash("Session expired.", "danger")
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("index"))

    password = request.form.get("password")
    confirm = request.form.get("confirm_password")

    if password != confirm:
        flash("❌ Passwords do not match.", "danger")
        return redirect(url_for("index", reset=1))

    user.set_password(password)

    user.verification_code = None
    user.verification_expiry = None

    db.session.commit()

    session.pop("reset_email", None)

    flash("✅ Password changed successfully. You can now login.", "success")

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
# ==========================================
# 👤 PROFILE
# ==========================================

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

            os.makedirs(upload_folder, exist_ok=True)

            image.save(
                os.path.join(upload_folder, filename)
            )

            current_user.profile_image = filename

        db.session.commit()

        flash("Profile updated successfully 💕", "success")

        return redirect(url_for("profile"))

    # ==========================
    # Render
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

@app.route("/login", methods=["GET", "POST"])
def login():

    form = LoginForm()
    register_form = RegisterForm()
    verify_form = VerifyCodeForm()

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data.strip()
        ).first()

        # البريد الإلكتروني غير موجود
        if user is None:

            if session.get("language") == "ar":
                flash("❌ البريد الإلكتروني غير موجود.", "login_error")
            else:
                flash("❌ Email not found.", "login_error")

            return render_template(
                "index.html",
                products=products,
                form=form,
                register_form=register_form,
                verify_form=verify_form,
                login_error=True
            )

        # كلمة المرور خاطئة
        if not user.check_password(form.password.data):

            if session.get("language") == "ar":
                flash("❌ كلمة المرور غير صحيحة.", "login_error")
            else:
                flash("❌ Incorrect password.", "login_error")

            return render_template(
                "index.html",
                products=products,
                form=form,
                register_form=register_form,
                verify_form=verify_form,
                login_error=True
            )

        # الحساب غير مفعل
        if not user.confirmed:

            session["verify_email"] = user.email

            if session.get("language") == "ar":
                flash("📧 يرجى تأكيد بريدك الإلكتروني أولاً.", "login_warning")
            else:
                flash("📧 Please verify your email first.", "login_warning")

            return redirect(url_for("index", verify=1))

        # ==========================
        # تسجيل الدخول
        # ==========================

        login_user(user, remember=True)

        # حفظ معرف المستخدم في الـ session
        session["user_id"] = user.id

        session["is_admin"] = (user.role == "admin")

        merge_session_cart_into_db(user.id)

        if user.role == "admin":
            return redirect(url_for("admin_home"))

        return redirect(url_for("home_logged"))

    # إذا كان النموذج غير صالح
    if request.method == "POST":

        if session.get("language") == "ar":
            flash("❌ يرجى التحقق من البيانات.", "login_error")
        else:
            flash("❌ Please check your information.", "login_error")

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

    print("Before logout:", current_user.is_authenticated)

    logout_user()

    print("After logout:", current_user.is_authenticated)

    flash("👋 You have been logged out.", "info")

    return redirect(url_for("index"))

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

@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():

    data = request.get_json() or {}

    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    if not product_id:
        return jsonify({
            "success": False,
            "error": "No product_id provided"
        }), 400

    product = Product.query.get(product_id)

    if not product:
        return jsonify({
            "success": False,
            "error": "Product not found"
        }), 404

    user_id = session.get("user_id")

    if user_id:

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

        return jsonify({
            "success": True,
            "message": "Product added to cart (DB)!"
        })

    cart = session_get_cart()

    found = False

    for item in cart:

        if item["product_id"] == product_id:
            item["quantity"] += quantity
            found = True
            break

    if not found:

        cart.append({
            "product_id": product_id,
            "quantity": quantity
        })

    session_save_cart(cart)

    return jsonify({
        "success": True,
        "message": "Product added to cart (Session)!"
    })


@app.route("/api/cart")
def api_cart_get():

    user_id = session.get("user_id")

    if user_id:

        cart_items = get_db_cart_items(user_id)

        return jsonify({
            "cart": cart_items_to_json(cart_items)
        })

    session_cart = session_get_cart()

    output = []

    for item in session_cart:

        product = Product.query.get(item["product_id"])

        if not product:
            continue

        output.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "quantity": item["quantity"],
            "image": url_for(
                "static",
                filename=f"images/{product.image}"
            ) if product.image else ""
        })

    return jsonify({
        "cart": output
    })


# ==========================================
# 🗑 Remove Product From Cart
# ==========================================

@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():

    data = request.get_json() or {}

    product_id = data.get("product_id")

    if not product_id:
        return jsonify({
            "success": False,
            "error": "No product_id provided"
        }), 400

    user_id = session.get("user_id")

    # إذا المستخدم مسجل دخول
    if user_id:

        item = Cart.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()

        if item:
            db.session.delete(item)
            db.session.commit()

        return jsonify({
            "success": True
        })

    # إذا ضيف (Session)
    cart = session_get_cart()

    cart = [
        item for item in cart
        if item["product_id"] != product_id
    ]

    session_save_cart(cart)

    return jsonify({
        "success": True
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
def checkout_page():
    return render_template("checkout.html")


@app.route("/api/checkout", methods=["POST"])
def api_checkout():

    data = request.get_json() or {}

    name = data.get("name", "").strip()
    address = data.get("address", "").strip()

    if not name or not address:
        return jsonify({
            "error": "Please complete all information."
        }), 400

    user_id = session.get("user_id")

    # ===============================
    # البريد الإلكتروني
    # ===============================
    customer_email = ""

    if user_id:
        user = User.query.get(user_id)
        if user:
            customer_email = user.email

    cart_entries = []
    total = 0

    # ===============================
    # مستخدم مسجل
    # ===============================
    if user_id:

        db_cart = get_db_cart_items(user_id)

        for item in db_cart:

            product = Product.query.get(item.product_id)

            if not product:
                continue

            total += product.price * item.quantity

            cart_entries.append({
                "product": product,
                "quantity": item.quantity
            })

    # ===============================
    # زائر
    # ===============================
    else:

        for item in session_get_cart():

            product = Product.query.get(item["product_id"])

            if not product:
                continue

            total += product.price * item["quantity"]

            cart_entries.append({
                "product": product,
                "quantity": item["quantity"]
            })

    # ===============================
    # إذا السلة فارغة
    # ===============================
    if not cart_entries:

        return jsonify({
            "error": "Cart is empty."
        }), 400

    # ===============================
    # إنشاء الطلب
    # ===============================
    order = Order(

        user_id=user_id,
        customer_name=name,
        customer_email=customer_email,
        address=address,
        payment_method="",
        total=total,

        # يبدأ دائماً بانتظار المراجعة
        status="Pending Review"

    )

    db.session.add(order)
    db.session.flush()

    # ===============================
    # إضافة المنتجات
    # ===============================
    for entry in cart_entries:

        product = entry["product"]

        db.session.add(

            OrderItem(

                order_id=order.id,
                product_id=product.id,
                quantity=entry["quantity"],
                price=product.price

            )

        )

    # ===============================
    # تفريغ السلة
    # ===============================
    if user_id:

        Cart.query.filter_by(user_id=user_id).delete()

    else:

        session_save_cart([])

    # ===============================
    # إنشاء إشعار للأدمن
    # ===============================
    notification = Notification(
        message=f"🛍️ طلب جديد رقم #{order.id} من العميل {order.customer_name}"
    )

    db.session.add(notification)

    # حفظ الطلب والإشعار معاً
    db.session.commit()

    # ===============================
    # إرسال إيميل للأدمن
    # ===============================
    try:

        products_text = ""

        for entry in cart_entries:

            product = entry["product"]

            products_text += (
                f"• {product.name}\n"
                f"   الكمية: {entry['quantity']}\n"
                f"   السعر: {product.price:.2f} ر.س\n\n"
            )

        msg = MailMessage(

            subject=f"🛍️ طلب جديد رقم #{order.id}",

            recipients=["rema7122002@gmail.com"]

        )

        msg.body = f"""
السلام عليكم،

لديك طلب جديد في متجر Crochet Rory Store 🎉

━━━━━━━━━━━━━━━━━━━━━━

📦 رقم الطلب:
#{order.id}

👤 اسم العميل:
{order.customer_name}

📧 البريد الإلكتروني:
{order.customer_email if order.customer_email else "لا يوجد"}

📍 عنوان التوصيل:
{order.address}

━━━━━━━━━━━━━━━━━━━━━━

🛍️ تفاصيل الطلب:

{products_text}

━━━━━━━━━━━━━━━━━━━━━━

💰 إجمالي الطلب:
{order.total:.2f} ر.س

━━━━━━━━━━━━━━━━━━━━━━

الحالة الحالية:
بانتظار المراجعة

يرجى تسجيل الدخول إلى لوحة التحكم لمراجعة الطلب.

مع تحيات،
Crochet Rory Store
"""

        mail.send(msg)

    except Exception as e:

        print("Order Mail Error:", e)

    return jsonify({

        "success": True,
        "order_id": order.id

    })

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
@app.before_request
def count_visitors():

    # لا نسجل ملفات static
    if request.path.startswith("/static"):
        return

    visitor = Visitor(
        ip_address=request.remote_addr,
        page=request.path
    )

    db.session.add(visitor)
    db.session.commit()
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


@app.route("/admin/home")
@login_required
def admin_home():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    return render_template(
        "admin/admin_home.html",

        product_count=Product.query.count(),

        order_count=Order.query.count(),

        user_count=User.query.count(),

        visitor_count=Visitor.query.count(),

        new_messages=Message.query.filter_by(
            is_read=False
        ).count(),

        orders=Order.query.order_by(
            Order.id.desc()
        ).limit(5).all()
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
@app.context_processor
def inject_admin_notifications():

    unread_notifications = Notification.query.filter_by(
        is_read=False
    ).count()

    return dict(
        unread_notifications=unread_notifications
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
# 🧶 ADD PRODUCT
# ==========================================

@login_required
def add_product():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    form = ProductForm()

    if form.validate_on_submit():

        filename = None

        if form.image.data:

            image_file = form.image.data
            filename = secure_filename(image_file.filename)

            image_file.save(
                os.path.join(
                    app.root_path,
                    "static",
                    "images",
                    filename
                )
            )

        product = Product(
            name=form.name.data,
            price=form.price.data,
            description=form.description.data,
            image=filename,
            publish_location=form.publish_location.data
        )

        db.session.add(product)
        db.session.commit()

        flash(
            "✅ Product added successfully!",
            "success"
        )

        return redirect(url_for("admin_products"))

    return render_template(
        "admin/add_product.html",
        form=form
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

@app.route('/admin/products')
@login_required
def admin_products():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    products = Product.query.all()

    return render_template(
        "admin/admin_products.html",
        products=products
    )


@app.route('/admin/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    product = Product.query.get_or_404(id)
    form = AddProductForm(obj=product)

    if form.validate_on_submit():

        product.name = form.name.data
        product.price = form.price.data
        product.description = form.description.data
        product.publish_location = form.publish_location.data

        if form.image.data:
            image = form.image.data
            filename = secure_filename(image.filename)

            image_path = os.path.join(
                app.root_path,
                "static",
                "images",
                filename
            )

            image.save(image_path)
            product.image = filename

        db.session.commit()

        flash("✅ Product updated successfully!", "success")
        return redirect(url_for("admin_products"))

    return render_template(
        "admin/edit_product.html",
        form=form,
        product=product,
        edit_mode=True
    )


@app.route('/admin/delete_product/<int:id>', methods=['POST'])
@login_required
def delete_product(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    product = Product.query.get_or_404(id)

    db.session.delete(product)
    db.session.commit()

    flash(f"🗑️ Product '{product.name}' deleted successfully.", "success")

    return redirect(url_for("admin_products"))


# ==========================================
# 👥 USER MANAGEMENT
# ==========================================

@app.route('/admin/users')
@login_required
def admin_users():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    search = request.args.get("search", "")
    role_filter = request.args.get("role", "")

    users = User.query

    if search:
        users = users.filter(
            (User.username.contains(search)) |
            (User.email.contains(search))
        )

    if role_filter:
        users = users.filter_by(role=role_filter)

    users = users.all()

    return render_template(
        "admin/admin_users.html",
        users=users,
        search=search,
        role_filter=role_filter
    )


@app.route('/admin/make_admin/<int:id>', methods=['POST'])
@login_required
def make_admin(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    user = User.query.get_or_404(id)
    user.role = "admin"

    db.session.commit()

    flash(f"✅ {user.username} is now an Admin!", "success")

    return redirect(url_for("admin_users"))


@app.route('/admin/demote_user/<int:id>', methods=['POST'])
@login_required
def demote_user(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    user = User.query.get_or_404(id)

    if user.email == "admin@store.com":
        flash("❌ You cannot demote the main admin.", "danger")
    else:
        user.role = "user"
        db.session.commit()
        flash(f"⬇ {user.username} has been demoted to User.", "info")

    return redirect(url_for("admin_users"))


@app.route('/admin/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    user = User.query.get_or_404(id)

    if user.email == "admin@store.com":
        flash("⚠️ You cannot delete the main admin.", "warning")
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f"🗑️ User {user.username} deleted successfully.", "success")

    return redirect(url_for("admin_users"))


# ==========================================
# 📩 CONTACT
# ==========================================

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        message_text = request.form.get("message")

        new_message = Message(
            name=name,
            email=email,
            message=message_text
        )

        db.session.add(new_message)
        db.session.commit()

        flash("💖 Your message has been sent successfully!")

        return redirect(url_for("contact_page"))

    return render_template("contact.html")


# ==========================================
# 📨 ADMIN MESSAGES
# ==========================================

@app.route('/admin/messages')
@login_required
def admin_messages():

    if current_user.role != "admin":
        flash("⚠️ Access denied! Admins only.", "danger")
        return redirect(url_for("home_logged"))

    messages = Message.query.order_by(Message.id.desc()).all()

    return render_template(
        "admin/admin_messages.html",
        messages=messages
    )


# ==========================================
# 🏠 USER HOME
# ==========================================

@app.route("/home_logged", methods=["GET", "POST"])
@login_required
def home_logged():

    if request.method == "POST":

        review = Review(
            name=request.form["name"],
            message=request.form["message"],
            stars=int(request.form.get("stars", 5))
        )

        db.session.add(review)
        db.session.commit()

        flash("Thank you for your review! 💕")

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    reviews = Review.query.all()

    return render_template(
        "home_logged.html",
        products=products,
        reviews=reviews,
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