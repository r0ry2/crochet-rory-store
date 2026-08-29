"""Add size prices to product

Revision ID: d0b463955c6c

Revises: 8302f86b2a83

Create Date: 2026-08-28 00:36:20.397827

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0b463955c6c'
down_revision = '8302f86b2a83'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('size_prices', sa.JSON(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('size_prices')