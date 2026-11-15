"""Planes recibidos en la nave, planes y plantillas del lado de Tierra, y estado del enlace.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS groundlink")
    # Lado de la nave: cada plan que llega por el enlace (R9).
    op.execute(
        """
        CREATE TABLE groundlink.inbound_plan (
          id           uuid        PRIMARY KEY,
          batch_id     uuid        NOT NULL UNIQUE,
          plan_version int         NOT NULL,
          status       text        NOT NULL,
          payload_hash text        NOT NULL,
          reason       text,
          rejected     jsonb,
          received_at  timestamptz NOT NULL,
          applied_at   timestamptz,
          CONSTRAINT inbound_status_chk CHECK (status IN ('RECIBIDO', 'APLICADO', 'RECHAZADO'))
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX inbound_plan_version ON groundlink.inbound_plan (plan_version) "
        "WHERE status <> 'RECHAZADO'"
    )
    # Lado de Tierra (solo en la demo o en el despliegue de Tierra).
    op.execute(
        """
        CREATE TABLE groundlink.ground_plan (
          id           uuid        PRIMARY KEY,
          version      int         NOT NULL UNIQUE,
          status       text        NOT NULL DEFAULT 'BORRADOR',
          batch_id     uuid        UNIQUE,
          reason       text,
          published_at timestamptz,
          acked_at     timestamptz,
          CONSTRAINT ground_plan_status_chk CHECK (status IN ('BORRADOR', 'EN_COLA',
            'EN_EL_ENLACE', 'RECIBIDO', 'APLICADO', 'CONFIRMADO', 'RECHAZADO'))
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX ground_plan_one_draft ON groundlink.ground_plan ((true)) "
        "WHERE status = 'BORRADOR'"
    )
    op.execute(
        """
        CREATE TABLE groundlink.ground_item (
          id                 uuid PRIMARY KEY,
          plan_id            uuid NOT NULL REFERENCES groundlink.ground_plan (id),
          position           int  NOT NULL,
          change             text NOT NULL,
          target_template_id uuid NOT NULL,
          kind               text,
          title              text,
          recurrence         text,
          zone_code          text,
          UNIQUE (plan_id, target_template_id),
          CONSTRAINT ground_item_change_chk CHECK (change IN ('NEW', 'UPDATE', 'CANCEL'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE groundlink.link_state (
          id         int         PRIMARY KEY DEFAULT 1,
          online     boolean     NOT NULL DEFAULT true,
          delay_s    numeric     NOT NULL DEFAULT 2,
          changed_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT link_state_single CHECK (id = 1)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS groundlink.link_state")
    op.execute("DROP TABLE IF EXISTS groundlink.ground_item")
    op.execute("DROP TABLE IF EXISTS groundlink.ground_plan")
    op.execute("DROP TABLE IF EXISTS groundlink.inbound_plan")
