"""Outbox transaccional e inbox de idempotencia.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS platform")
    op.execute(
        """
        CREATE TABLE platform.outbox_event (
          id              bigserial   PRIMARY KEY,
          event_id        uuid        NOT NULL UNIQUE,
          type            text        NOT NULL,
          version         int         NOT NULL DEFAULT 1,
          aggregate_type  text        NOT NULL,
          aggregate_id    uuid        NOT NULL,
          partition_key   text        NOT NULL,
          correlation_id  uuid,
          causation_id    uuid,
          payload         jsonb       NOT NULL,
          occurred_at     timestamptz NOT NULL DEFAULT now(),
          status          text        NOT NULL DEFAULT 'pending',
          attempts        int         NOT NULL DEFAULT 0,
          next_attempt_at timestamptz NOT NULL DEFAULT now(),
          last_error      text,
          CONSTRAINT outbox_status_chk CHECK (status IN ('pending', 'done', 'dead'))
        )
        """
    )
    op.execute(
        "CREATE INDEX outbox_pending_idx ON platform.outbox_event (next_attempt_at, id) "
        "WHERE status = 'pending'"
    )
    op.execute(
        """
        CREATE TABLE platform.inbox_processed (
          consumer     text        NOT NULL,
          event_id     uuid        NOT NULL,
          processed_at timestamptz NOT NULL DEFAULT now(),
          PRIMARY KEY (consumer, event_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS platform.inbox_processed")
    op.execute("DROP TABLE IF EXISTS platform.outbox_event")
