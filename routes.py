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
    AddProductForm
)

from forms import (
    LoginForm,
    RegisterForm,
    ProductForm
)

from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user
)

from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer

from datetime import datetime
import os


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
        return jsonify({"error": "Order not found"}), 404

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
        "address": order.address,
        "total": order.total,
        "items": item_list
    })
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
# 🏠 GENERAL ROUTES
# ==========================================

@app.route("/", methods=["GET", "POST"])
def index():

    products = Product.query.filter(
        Product.publish_location.in_(
            ["both", "home_only"]
        )
    ).all()

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data
        ).first()

        if not user or not user.check_password(form.password.data):
            flash("❌ Invalid email or password!", "danger")
        else:
            login_user(user)
            session["is_admin"] = (user.role == "admin")
            merge_session_cart_into_db(user.id)

            if user.role == "admin":
                return redirect(url_for("admin_home"))

            return redirect(url_for("home_logged"))

    register_form = RegisterForm()

    return render_template(
        "index.html",
        products=products,
        form=form,
        register_form=register_form
    )



@app.route("/cart")
def cart_page():
    return render_template("cart.html")


# ==========================================
# 👤 REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    form = RegisterForm()

    print(form.errors)

    if form.validate_on_submit():

        existing_user = User.query.filter_by(
            email=form.email.data
        ).first()

        if existing_user:
            flash(
                "⚠️ Email already registered!",
                "warning"
            )
            return redirect(url_for("index"))

        new_user = User(
            username=form.username.data,
            email=form.email.data,
            phone=form.phone.data
        )

        new_user.set_password(form.password.data)

        if form.email.data == "admin@store.com":
            new_user.role = "admin"

        new_user.confirmed = True

        db.session.add(new_user)
        db.session.commit()

        flash(
            "✅ Registration successful! You can now log in.",
            "success"
        )

        return redirect(url_for("index"))

    login_form = LoginForm()

    products = Product.query.filter(
        Product.publish_location.in_(["both", "home_only"])
    ).all()

    return render_template(
        "index.html",
        products=products,
        form=login_form,
        register_form=form
    )


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

    pending_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).count()

    unpaid_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Unpaid"
    ).count()

    processing_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Processing"
    ).count()

    completed_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Completed"
    ).count()

    cancelled_orders = Order.query.filter_by(
        user_id=current_user.id,
        status="Cancelled"
    ).count()

    cart_count = Cart.query.filter_by(
        user_id=current_user.id
    ).count()

    wishlist_count = 0

    # ==========================
    # Orders Lists
    # ==========================

    all_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Order.created_at.desc()
    ).all()

    pending_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Pending"
    ).all()

    unpaid_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Unpaid"
    ).all()

    processing_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Processing"
    ).all()

    completed_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Completed"
    ).all()

    cancelled_list = Order.query.filter_by(
        user_id=current_user.id,
        status="Cancelled"
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

    return render_template(
        "profile.html",

        user=current_user,

        total_orders=total_orders,
        pending_orders=pending_orders,
        unpaid_orders=unpaid_orders,
        processing_orders=processing_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,

        cart_count=cart_count,
        wishlist_count=wishlist_count,

        orders=all_orders,
        pending_list=pending_list,
        unpaid_list=unpaid_list,
        processing_list=processing_list,
        completed_list=completed_list,
        cancelled_list=cancelled_list
    )

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

    print("========== LOGIN ==========")
    print("Method:", request.method)
    print("Form Data:", request.form)

    form = LoginForm()

    print("Method:", request.method)
    print("Form valid:", form.validate_on_submit())
    print("Errors:", form.errors)

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data
        ).first()

        print("========== LOGIN DEBUG ==========")
        print("Email entered:", form.email.data)
        print("Password entered:", form.password.data)
        print("User found:", user)

        if user:
            print("Database email:", user.email)
            print("Password hash:", user.password_hash)
            print("Password correct:", user.check_password(form.password.data))

        if user is None:
            flash("❌ Email not found.", "danger")
            return redirect(url_for("index"))

        if not user.check_password(form.password.data):
            flash("❌ Wrong password.", "danger")
            return redirect(url_for("index"))

        login_user(user, remember=True)

        session["is_admin"] = (user.role == "admin")

        merge_session_cart_into_db(user.id)

        print("✅ LOGIN SUCCESS")

        if user.role == "admin":
            return redirect(url_for("admin_home"))

        return redirect(url_for("home_logged"))

    flash("❌ Please check your information.", "danger")
    return redirect(url_for("index"))
# ==========================================
# 🚪 LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash(
        "👋 You have been logged out.",
        "info"
    )

    return redirect(url_for("login"))


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

    name = data.get("name") or "Guest"
    address = data.get("address") or ""

    user_id = session.get("user_id")

    cart_entries = []
    total = 0

    if user_id:

        db_cart = get_db_cart_items(user_id)

        if not db_cart:
            return jsonify({"error": "Cart is empty"}), 400

        for item in db_cart:

            product = Product.query.get(item.product_id)

            if not product:
                continue

            total += product.price * item.quantity

            cart_entries.append({
                "product": product,
                "quantity": item.quantity
            })

    else:

        for item in session_get_cart():

            product = Product.query.get(item["product_id"])

            if not product:
                continue

            quantity = item["quantity"]

            total += product.price * quantity

            cart_entries.append({
                "product": product,
                "quantity": quantity
            })

    order = Order(
        user_id=user_id,
        customer_name=name,
        address=address,
        total=0
    )

    db.session.add(order)
    db.session.flush()

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

        if user_id:

            cart_item = Cart.query.filter_by(
                user_id=user_id,
                product_id=product.id
            ).first()

            if cart_item:
                db.session.delete(cart_item)

    order.total = total

    db.session.commit()

    if not user_id:
        session_save_cart([])

    return jsonify({
        "message": "Checkout successful!",
        "order_id": order.id,
        "total": order.total
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
        new_messages=Message.query.filter_by(is_read=False).count(),
        orders=Order.query.order_by(Order.id.desc()).limit(5).all()
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