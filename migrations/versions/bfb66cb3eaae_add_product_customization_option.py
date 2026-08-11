"""Add product customization option

Revision ID: bfb66cb3eaae
Revises: 20c5b6c9bae0
Create Date: 2026-08-10 05:27:36.333204

"""

from alembic import op
import sqlalchemy as sa


# ==================================================
# Revision identifiers
# ==================================================

revision = "bfb66cb3eaae"

down_revision = "20c5b6c9bae0"

branch_labels = None

depends_on = None


# ==================================================
# UPGRADE
# ==================================================

def upgrade():

    # ==================================================
    # 🧸 PRODUCT TABLE
    # ==================================================

    with op.batch_alter_table(
        "product",
        schema=None
    ) as batch_op:

        # ==========================
        # ✨ Customization
        # ==========================

        batch_op.add_column(
            sa.Column(
                "is_customizable",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false()
            )
        )

        # ==========================
        # 🛒 Purchase Count
        # ==========================

        batch_op.add_column(
            sa.Column(
                "purchase_count",
                sa.Integer(),
                nullable=False,
                server_default="0"
            )
        )

        # ==========================
        # 📅 Created At
        # ==========================

        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True
            )
        )


# ==================================================
# DOWNGRADE
# ==================================================

def downgrade():

    with op.batch_alter_table(
        "product",
        schema=None
    ) as batch_op:

        # ==========================
        # 📅 Created At
        # ==========================

        batch_op.drop_column(
            "created_at"
        )

        # ==========================
        # 🛒 Purchase Count
        # ==========================

        batch_op.drop_column(
            "purchase_count"
        )

        # ==========================
        # ✨ Customization
        # ==========================

        batch_op.drop_column(
            "is_customizable"
        )