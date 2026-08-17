"""Update visitor table

Revision ID: 49936bde13b2
Revises: 506b686262ee
Create Date: 2026-08-15 18:08:28.768446

"""

from alembic import op
import sqlalchemy as sa


# ============================================================
# Revision identifiers
# ============================================================

revision = "49936bde13b2"
down_revision = "506b686262ee"
branch_labels = None
depends_on = None


def upgrade():

    connection = op.get_bind()

    # ========================================================
    # 1. Fix existing NULL values
    # ========================================================

    connection.execute(
        sa.text(
            """
            UPDATE visitor
            SET visitor_id = 'legacy-' || CAST(id AS VARCHAR)
            WHERE visitor_id IS NULL
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE visitor
            SET visitor_type = 'guest'
            WHERE visitor_type IS NULL
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE visitor
            SET started_at = CURRENT_TIMESTAMP
            WHERE started_at IS NULL
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE visitor
            SET last_activity = CURRENT_TIMESTAMP
            WHERE last_activity IS NULL
            """
        )
    )

    # ========================================================
    # 2. Remove leftover temporary table if migration
    #    was interrupted previously
    # ========================================================

    connection.execute(
        sa.text(
            "DROP TABLE IF EXISTS _alembic_tmp_visitor"
        )
    )

    # ========================================================
    # 3. Create new visitor table
    #
    # IMPORTANT:
    # PostgreSQL treats "user" as a reserved keyword.
    # Therefore it MUST be quoted as "user".
    # ========================================================

    connection.execute(
        sa.text(
            """
            CREATE TABLE _alembic_tmp_visitor (
                id INTEGER NOT NULL,
                ip_address VARCHAR(100),
                page VARCHAR(255),
                visited_at TIMESTAMP NOT NULL,
                visitor_id VARCHAR(100) NOT NULL,
                user_id INTEGER,
                visitor_type VARCHAR(20) NOT NULL,
                started_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT fk_visitor_user_id
                    FOREIGN KEY(user_id)
                    REFERENCES "user" (id)
            )
            """
        )
    )

    # ========================================================
    # 4. Copy existing data
    # ========================================================

    connection.execute(
        sa.text(
            """
            INSERT INTO _alembic_tmp_visitor (
                id,
                ip_address,
                page,
                visited_at,
                visitor_id,
                user_id,
                visitor_type,
                started_at,
                last_activity
            )
            SELECT
                id,
                ip_address,
                page,
                visited_at,
                visitor_id,
                user_id,
                visitor_type,
                started_at,
                last_activity
            FROM visitor
            """
        )
    )

    # ========================================================
    # 5. Remove old table
    # ========================================================

    connection.execute(
        sa.text(
            "DROP TABLE visitor"
        )
    )

    # ========================================================
    # 6. Rename temporary table
    # ========================================================

    connection.execute(
        sa.text(
            """
            ALTER TABLE _alembic_tmp_visitor
            RENAME TO visitor
            """
        )
    )


def downgrade():

    connection = op.get_bind()

    # ========================================================
    # 1. Remove leftover temporary table
    # ========================================================

    connection.execute(
        sa.text(
            "DROP TABLE IF EXISTS _alembic_tmp_visitor"
        )
    )

    # ========================================================
    # 2. Create old visitor structure
    # ========================================================

    connection.execute(
        sa.text(
            """
            CREATE TABLE _alembic_tmp_visitor (
                id INTEGER NOT NULL,
                ip_address VARCHAR(100),
                page VARCHAR(255),
                visited_at TIMESTAMP NOT NULL,
                visitor_id VARCHAR(100),
                user_id INTEGER,
                visitor_type VARCHAR(20),
                started_at TIMESTAMP,
                last_activity TIMESTAMP,
                PRIMARY KEY (id),
                CONSTRAINT fk_visitor_user_id
                    FOREIGN KEY(user_id)
                    REFERENCES "user" (id)
            )
            """
        )
    )

    # ========================================================
    # 3. Copy data back
    # ========================================================

    connection.execute(
        sa.text(
            """
            INSERT INTO _alembic_tmp_visitor (
                id,
                ip_address,
                page,
                visited_at,
                visitor_id,
                user_id,
                visitor_type,
                started_at,
                last_activity
            )
            SELECT
                id,
                ip_address,
                page,
                visited_at,
                visitor_id,
                user_id,
                visitor_type,
                started_at,
                last_activity
            FROM visitor
            """
        )
    )

    # ========================================================
    # 4. Remove current table
    # ========================================================

    connection.execute(
        sa.text(
            "DROP TABLE visitor"
        )
    )

    # ========================================================
    # 5. Restore old table
    # ========================================================

    connection.execute(
        sa.text(
            """
            ALTER TABLE _alembic_tmp_visitor
            RENAME TO visitor
            """
        )
    )