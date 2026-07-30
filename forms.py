from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField

from wtforms import (
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
                ["jpg", "jpeg", "png"],
                "Images only!"
            )
        ]
    )

    publish_location = SelectField(
        "Publish Product",
        choices=[
            ("both", "Show in Home + Products pages"),
            ("products_only", "Show only in Products page")
        ],
        default="products_only"
    )

    submit = SubmitField("Save")


# ==================================================
# 👤 REGISTER FORM
# ==================================================
class RegisterForm(FlaskForm):

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=25)
        ]
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )
    phone = StringField(
    "Phone Number",
    validators=[
        DataRequired(),
        Length(min=8, max=15)
    ]
)

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6)
        ]
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password")
        ]
    )

    submit = SubmitField("Register")


# ==================================================
# 🔐 LOGIN FORM
# ==================================================
class LoginForm(FlaskForm):

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )


    password = PasswordField(
        "Password",
        validators=[DataRequired()]
    )

    submit = SubmitField("Login")

# ==================================================
# 📧 VERIFY EMAIL FORM
# ==================================================
class VerifyCodeForm(FlaskForm):

    code = StringField(
        "Verification Code",
        validators=[
            DataRequired(),
            Length(min=6, max=6)
        ]
    )

    submit = SubmitField("Verify")