"""Update visitor tracking system

Revision ID: 506b686262ee
Revises: bfc4bb41a00e
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "506b686262ee"

down_revision = "bfc4bb41a00e"

branch_labels = None

depends_on = None


def upgrade():

    with op.batch_alter_table(
        "visitor",
        schema=None
    ) as batch_op:

        # ==================================================
        # VISITOR ID
        # ==================================================

        batch_op.add_column(
            sa.Column(
                "visitor_id",
                sa.String(length=100),
                nullable=True
            )
        )


        # ==================================================
        # USER ID
        # ==================================================

        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.Integer(),
                nullable=True
            )
        )


        # ==================================================
        # VISITOR TYPE
        # ==================================================

        batch_op.add_column(
            sa.Column(
                "visitor_type",
                sa.String(length=20),
                nullable=True
            )
        )


        # ==================================================
        # STARTED AT
        # ==================================================

        batch_op.add_column(
            sa.Column(
                "started_at",
                sa.DateTime(),
                nullable=True
            )
        )


        # ==================================================
        # LAST ACTIVITY
        # ==================================================

        batch_op.add_column(
            sa.Column(
                "last_activity",
                sa.DateTime(),
                nullable=True
            )
        )


        # ==================================================
        # INDEXES
        # ==================================================

        batch_op.create_index(
            "ix_visitor_visitor_id",
            ["visitor_id"],
            unique=False
        )

        batch_op.create_index(
            "ix_visitor_user_id",
            ["user_id"],
            unique=False
        )


        # ==================================================
        # FOREIGN KEY
        # ==================================================

        batch_op.create_foreign_key(
            "fk_visitor_user_id",
            "user",
            ["user_id"],
            ["id"]
        )


        # ==================================================
        # VISITED AT
        # ==================================================

        batch_op.alter_column(
            "visited_at",
            existing_type=sa.DateTime(),
            nullable=False
        )


def downgrade():

    with op.batch_alter_table(
        "visitor",
        schema=None
    ) as batch_op:

        batch_op.drop_constraint(
            "fk_visitor_user_id",
            type_="foreignkey"
        )

        batch_op.drop_index(
            "ix_visitor_user_id"
        )

        batch_op.drop_index(
            "ix_visitor_visitor_id"
        )

        batch_op.drop_column(
            "last_activity"
        )

        batch_op.drop_column(
            "started_at"
        )

        batch_op.drop_column(
            "visitor_type"
        )

        batch_op.drop_column(
            "user_id"
        )

        batch_op.drop_column(
            "visitor_id"
        )

        batch_op.alter_column(
            "visited_at",
            existing_type=sa.DateTime(),
            nullable=True
        )