"""Add cart and order item size fields

Revision ID: e14125650e29

Revises: d0b463955c6c

Create Date: 2026-08-28 03:46:46.196768

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e14125650e29"
down_revision = "d0b463955c6c"
branch_labels = None
depends_on = None


def upgrade():

    # ==========================================
    # 🛒 CART
    # ==========================================

    with op.batch_alter_table(
        "cart",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "selected_size",
                sa.String(length=50),
                nullable=True
            )
        )

        batch_op.add_column(
            sa.Column(
                "selected_price",
                sa.Float(),
                nullable=True
            )
        )

    # ==========================================
    # 🧾 ORDER ITEM
    # ==========================================

    with op.batch_alter_table(
        "order_item",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "selected_size",
                sa.String(length=50),
                nullable=True
            )
        )


def downgrade():

    # ==========================================
    # 🧾 ORDER ITEM
    # ==========================================

    with op.batch_alter_table(
        "order_item",
        schema=None
    ) as batch_op:

        batch_op.drop_column(
            "selected_size"
        )

    # ==========================================
    # 🛒 CART
    # ==========================================

    with op.batch_alter_table(
        "cart",
        schema=None
    ) as batch_op:

        batch_op.drop_column(
            "selected_price"
        )

        batch_op.drop_column(
            "selected_size"
        )