"""Update Message model for chat

Revision ID: e32e3f3380c4
Revises: 7fc7ec8031a6
Create Date: 2026-08-31

"""

from alembic import op
import sqlalchemy as sa


# ==================================================
# REVISION IDENTIFIERS
# ==================================================

revision = "e32e3f3380c4"
down_revision = "7fc7ec8031a6"
branch_labels = None
depends_on = None


# ==================================================
# UPGRADE
# ==================================================

def upgrade():

    # ==================================================
    # MESSAGE TABLE
    # ==================================================

    with op.batch_alter_table("message", schema=None) as batch_op:

        # Customer/User ID
        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=True
            )
        )

        # Sender
        batch_op.add_column(
            sa.Column(
                "sender",
                sa.String(length=20),
                nullable=True
            )
        )

        # Message creation time
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True
            )
        )

        # Named Foreign Key
        batch_op.create_foreign_key(
            "fk_message_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )


# ==================================================
# DOWNGRADE
# ==================================================

def downgrade():

    with op.batch_alter_table("message", schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_message_user_id_user",
            type_="foreignkey"
        )

        batch_op.drop_column("created_at")
        batch_op.drop_column("sender")
        batch_op.drop_column("user_id")