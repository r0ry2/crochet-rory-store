"""Add customization to order items

Revision ID: 7fc7ec8031a6
Revises: 7831d4053093
Create Date: 2026-08-30 15:47:47.064127

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7fc7ec8031a6"
down_revision = "7831d4053093"
branch_labels = None
depends_on = None


def upgrade():
    # ==================================================
    # CART
    # ==================================================

    with op.batch_alter_table("cart", schema=None) as batch_op:

        # إضافة ON DELETE CASCADE بدون محاولة حذف
        # Foreign Key غير مسمى.
        batch_op.create_foreign_key(
            "fk_cart_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )


    # ==================================================
    # WISHLIST
    # ==================================================

    with op.batch_alter_table("wishlist", schema=None) as batch_op:

        # إضافة ON DELETE CASCADE بدون محاولة حذف
        # Foreign Key غير مسمى.
        batch_op.create_foreign_key(
            "fk_wishlist_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )


def downgrade():

    # ==================================================
    # WISHLIST
    # ==================================================

    with op.batch_alter_table("wishlist", schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_wishlist_user_id_user",
            type_="foreignkey"
        )


    # ==================================================
    # CART
    # ==================================================

    with op.batch_alter_table("cart", schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_cart_user_id_user",
            type_="foreignkey"
        )