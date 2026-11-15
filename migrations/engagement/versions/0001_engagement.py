"""Plantillas de tareas, tareas del día y planes de Tierra aplicados.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS engagement")
    op.execute(
        """
        CREATE TABLE engagement.task_template (
          id           uuid        PRIMARY KEY,
          kind         text        NOT NULL,
          title        text        NOT NULL,
          recurrence   text        NOT NULL,
          zone_code    text,
          origin       text        NOT NULL,
          active       boolean     NOT NULL DEFAULT true,
          due_time     text        NOT NULL DEFAULT '12:00',
          plan_version int,
          updated_at   timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT template_kind_chk CHECK (kind IN ('SALUD', 'NAVE')),
          CONSTRAINT template_origin_chk CHECK (origin IN ('TIERRA', 'SISTEMA', 'TRIPULACION')),
          CONSTRAINT template_recurrence_chk CHECK (recurrence IN ('DIARIA', 'UNA_VEZ'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE engagement.task (
          id              uuid        PRIMARY KEY,
          crew_member_id  uuid        NOT NULL,
          template_id     uuid        REFERENCES engagement.task_template (id),
          origin          text        NOT NULL,
          kind            text        NOT NULL,
          title           text        NOT NULL,
          zone_id         uuid,
          day             date        NOT NULL,
          due_at          timestamptz NOT NULL,
          status          text        NOT NULL DEFAULT 'PENDIENTE',
          blocked_reason  text,
          effective       boolean,
          completed_at    timestamptz,
          source_alert_id uuid,
          incident_id     uuid,
          action_key      text,
          created_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT task_kind_chk CHECK (kind IN ('SALUD', 'NAVE', 'INCIDENTE')),
          CONSTRAINT task_origin_chk CHECK (origin IN ('TIERRA', 'SISTEMA', 'TRIPULACION')),
          CONSTRAINT task_status_chk CHECK (status IN ('PENDIENTE', 'COMPLETADA', 'BLOQUEADA'))
        )
        """
    )
    # Idempotencia de lo que crea el sistema: una tarea por plantilla y día, una por incidente
    # y una por acción de cada alerta.
    op.execute(
        "CREATE UNIQUE INDEX task_template_day ON engagement.task (template_id, day) "
        "WHERE template_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX task_incident ON engagement.task (incident_id) "
        "WHERE incident_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX task_alert_action ON engagement.task (source_alert_id, action_key) "
        "WHERE source_alert_id IS NOT NULL"
    )
    op.execute("CREATE INDEX task_day_idx ON engagement.task (day, due_at)")
    op.execute(
        """
        CREATE TABLE engagement.applied_plan (
          plan_version int         PRIMARY KEY,
          batch_id     uuid        NOT NULL,
          applied      jsonb       NOT NULL,
          rejected     jsonb       NOT NULL,
          applied_at   timestamptz NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS engagement.applied_plan")
    op.execute("DROP TABLE IF EXISTS engagement.task")
    op.execute("DROP TABLE IF EXISTS engagement.task_template")
