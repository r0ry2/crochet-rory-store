"""Update visitor table

Revision ID: 49936bde13b2
Revises: 506b686262ee
Create Date: 2026-08-15 18:08:28.768446

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "49936bde13b2"
down_revision = "506b686262ee"
branch_labels = None
depends_on = None


def upgrade():

    # ==================================================
    # 1. Fix existing NULL values first
    # ==================================================

    op.execute(
        """
        UPDATE visitor
        SET visitor_id = 'legacy-' || id
        WHERE visitor_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE visitor
        SET visitor_type = 'guest'
        WHERE visitor_type IS NULL
        """
    )

    op.execute(
        """
        UPDATE visitor
        SET started_at = CURRENT_TIMESTAMP
        WHERE started_at IS NULL
        """
    )

    op.execute(
        """
        UPDATE visitor
        SET last_activity = CURRENT_TIMESTAMP
        WHERE last_activity IS NULL
        """
    )

    # ==================================================
    # 2. SQLite-safe table recreation
    # ==================================================

    connection = op.get_bind()

    # Remove any leftover temporary table
    connection.execute(
        sa.text(
            "DROP TABLE IF EXISTS _alembic_tmp_visitor"
        )
    )

    # Create the new visitor table manually
    connection.execute(
        sa.text(
            """
            CREATE TABLE _alembic_tmp_visitor (
                id INTEGER NOT NULL,
                ip_address VARCHAR(100),
                page VARCHAR(255),
                visited_at DATETIME NOT NULL,
                visitor_id VARCHAR(100) NOT NULL,
                user_id INTEGER,
                visitor_type VARCHAR(20) NOT NULL,
                started_at DATETIME NOT NULL,
                last_activity DATETIME NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT fk_visitor_user_id
                    FOREIGN KEY(user_id)
                    REFERENCES user (id)
            )
            """
        )
    )

    # Copy existing visitor data
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

    # Replace old table
    connection.execute(
        sa.text(
            "DROP TABLE visitor"
        )
    )

    connection.execute(
        sa.text(
            "ALTER TABLE _alembic_tmp_visitor RENAME TO visitor"
        )
    )


def downgrade():

    connection = op.get_bind()

    connection.execute(
        sa.text(
            "DROP TABLE IF EXISTS _alembic_tmp_visitor"
        )
    )

    connection.execute(
        sa.text(
            """
            CREATE TABLE _alembic_tmp_visitor (
                id INTEGER NOT NULL,
                ip_address VARCHAR(100),
                page VARCHAR(255),
                visited_at DATETIME NOT NULL,
                visitor_id VARCHAR(100),
                user_id INTEGER,
                visitor_type VARCHAR(20),
                started_at DATETIME,
                last_activity DATETIME,
                PRIMARY KEY (id),
                CONSTRAINT fk_visitor_user_id
                    FOREIGN KEY(user_id)
                    REFERENCES user (id)
            )
            """
        )
    )

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

    connection.execute(
        sa.text(
            "DROP TABLE visitor"
        )
    )

    connection.execute(
        sa.text(
            "ALTER TABLE _alembic_tmp_visitor RENAME TO visitor"
        )
    )