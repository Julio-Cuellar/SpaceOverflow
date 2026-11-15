"""Sequential ticket number, to display it as INC-0001.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tickets that already existed receive their number when the column is added.
    op.execute(
        "ALTER TABLE facility.incident ADD COLUMN number bigint GENERATED ALWAYS AS IDENTITY"
    )
    op.execute("ALTER TABLE facility.incident ADD CONSTRAINT incident_number_uk UNIQUE (number)")


def downgrade() -> None:
    op.execute("ALTER TABLE facility.incident DROP COLUMN number")
