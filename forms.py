from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField

from wtforms import (
    BooleanField,
    FloatField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField
)

from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length
)


# ==================================================
# 🧶 PRODUCT FORM
# ==================================================

class ProductForm(FlaskForm):

    # ==========================
    # 🧵 Product Name
    # ==========================

    name = StringField(
        "Product Name",
        validators=[
            DataRequired()
        ]
    )

    # ==========================
    # 🏷️ Product Category
    # ==========================

    category = SelectField(
        "Category",
        choices=[
            ("dolls", "Dolls"),
            ("keychains", "Keychains"),
            ("pattern", "Pattern"),
            ("coaster", "Coaster"),
            ("ready_stock", "Ready Stock")
        ],
        validators=[
            DataRequired()
        ]
    )

    # ==========================
    # 💰 Product Price
    # ==========================

    price = FloatField(
        "Price",
        validators=[
            DataRequired()
        ]
    )

    # ==========================
    # 📜 Product Description
    # ==========================

    description = TextAreaField(
        "Description",
        validators=[
            DataRequired()
        ]
    )

    # ==========================
    # 🖼️ Product Image
    # ==========================

    image = FileField(
        "Product Image",
        validators=[
            FileAllowed(
                ["jpg", "jpeg", "png"],
                "Images only!"
            )
        ]
    )

    # ==========================
    # 📍 Publish Location
    # ==========================

    publish_location = SelectField(
        "Publish Product",
        choices=[
            (
                "both",
                "Show in Home + Products pages"
            ),
            (
                "products_only",
                "Show only in Products page"
            )
        ],
        default="products_only"
    )

    # ==========================
    # ✨ Customization
    # هل المنتج قابل للتخصيص؟
    # ==========================

    is_customizable = BooleanField(
        "Allow Customization",
        default=False
    )

    # ==========================
    # 💾 Submit
    # ==========================

    submit = SubmitField(
        "Save"
    )


# ==================================================
# 👤 REGISTER FORM
# ==================================================

class RegisterForm(FlaskForm):

    # ==========================
    # 👤 Username
    # ==========================

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(
                min=3,
                max=25
            )
        ]
    )

    # ==========================
    # 📧 Email
    # ==========================

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    # ==========================
    # 📱 Phone Number
    # ==========================

    phone = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Length(
                min=8,
                max=15
            )
        ]
    )

    # ==========================
    # 🔐 Password
    # ==========================

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(
                min=6
            )
        ]
    )

    # ==========================
    # 🔐 Confirm Password
    # ==========================

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password")
        ]
    )

    # ==========================
    # 📝 Submit
    # ==========================

    submit = SubmitField(
        "Register"
    )


# ==================================================
# 🔐 LOGIN FORM
# ==================================================

class LoginForm(FlaskForm):

    # ==========================
    # 📧 Email
    # ==========================

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    # ==========================
    # 🔑 Password
    # ==========================

    password = PasswordField(
        "Password",
        validators=[
            DataRequired()
        ]
    )

    # ==========================
    # 🔓 Submit
    # ==========================

    submit = SubmitField(
        "Login"
    )


# ==================================================
# 📧 VERIFY EMAIL FORM
# ==================================================

class VerifyCodeForm(FlaskForm):

    # ==========================
    # 🔢 Verification Code
    # ==========================

    code = StringField(
        "Verification Code",
        validators=[
            DataRequired(),
            Length(
                min=6,
                max=6
            )
        ]
    )

    # ==========================
    # ✅ Submit
    # ==========================

    submit = SubmitField(
        "Verify"
    )