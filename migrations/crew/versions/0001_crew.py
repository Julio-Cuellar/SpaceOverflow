"""Crew members of a habitat. No health data: wearables do not exist in this system.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS crew")
    # `habitat_id` has no foreign key: Facility owns the habitat and modules do not share tables.
    op.execute(
        """
        CREATE TABLE crew.member (
          id         uuid        PRIMARY KEY,
          habitat_id uuid        NOT NULL,
          code       text        NOT NULL,
          name       text        NOT NULL,
          role       text        NOT NULL,
          portrait   smallint    NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (habitat_id, code),
          CONSTRAINT member_portrait_chk CHECK (portrait BETWEEN 1 AND 4)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP SCHEMA crew CASCADE")
