"""Add advertisements

Revision ID: 8302f86b2a83
Revises: 330478b616fc
Create Date: 2026-08-24 20:57:39.910043

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8302f86b2a83"
down_revision = "330478b616fc"
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================
    # ADVERTISEMENT TABLE
    # =========================================================
    #
    # جدول advertisement موجود بالفعل في قاعدة البيانات،
    # لذلك لا نقوم بإنشائه مرة أخرى.
    #
    # هذه migration فقط تسجل أن التعديل أصبح مكتملًا
    # حتى يستطيع Alembic الانتقال للـ migration التالية.
    #
    pass


def downgrade():
    # =========================================================
    # DOWNGRADE
    # =========================================================
    #
    # لا نحذف جدول advertisement هنا لأنه كان موجودًا
    # في قاعدة البيانات قبل تسجيل هذه migration.
    #
    pass