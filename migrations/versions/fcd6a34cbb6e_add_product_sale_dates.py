"""Add product sale dates

Revision ID: fcd6a34cbb6e
Revises: 44e1b82b3459
Create Date: 2026-08-11 17:16:08.579076

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision = 'fcd6a34cbb6e'
down_revision = '44e1b82b3459'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('sale_start_date', sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('sale_end_date', sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('sale_end_date')
        batch_op.drop_column('sale_start_date')