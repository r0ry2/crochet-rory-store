"""Add customization to order items

Revision ID: 7831d4053093
Revises: f288292790c0
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7831d4053093"
down_revision = "f288292790c0"
branch_labels = None
depends_on = None


def upgrade():

    # ==========================================
    # 🧾 ADD CUSTOMIZATION TO ORDER ITEMS
    # ==========================================

    with op.batch_alter_table(
        "order_item",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "customization",
                sa.Text(),
                nullable=True
            )
        )


def downgrade():

    # ==========================================
    # 🔄 REMOVE CUSTOMIZATION
    # ==========================================

    with op.batch_alter_table(
        "order_item",
        schema=None
    ) as batch_op:

        batch_op.drop_column(
            "customization"
        )