"""Esquema GraphQL compuesto. Las consultas leen fachadas; las mutaciones llaman casos de uso.

Los errores esperados son tipos del esquema (`union`), no excepciones.
"""

from __future__ import annotations

import base64
from datetime import datetime
from enum import Enum
from typing import Annotated, cast
from uuid import UUID

import strawberry
from strawberry import Info
from strawberry.extensions import QueryDepthLimiter
from strawberry.scalars import JSON

from spaceapp.interfaces.graphql.context import Context
from spaceapp.interfaces.graphql.dashboard import build_dashboard
from spaceapp.modules.knowledge.domain import model as knowledge
from spaceapp.modules.monitoring.application.acknowledge_alert import (
    AlertAlreadyResolved,
    AlertNotFound,
    AlreadyAcknowledged,
)
from spaceapp.modules.monitoring.facade import AlertView, RuleView
from spaceapp.platform.ids import habitat_id as habitat_id_of
from spaceapp.platform.vocab import Citation as CitationDTO

MAX_DEPTH = 10
MAX_PAGE = 100

GqlInfo = Info[Context, None]


# --- Enumeraciones -------------------------------------------------------------------------


@strawberry.enum
class Severity(Enum):
    NORMAL = "normal"
    ATENCION = "atencion"
    ALERTA = "alerta"
    CRITICO = "critico"


@strawberry.enum
class EvidenceState(Enum):
    VERIFICADO = "VERIFICADO"
    TB = "TB"
    DEMO = "DEMO"
    NO_VERIFICADO = "NO_VERIFICADO"


@strawberry.enum
class DataOrigin(Enum):
    REAL = "REAL"
    SIMULATED = "SIMULATED"
    REPLAY = "REPLAY"


@strawberry.enum
class AlertStatus(Enum):
    RAISED = "raised"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@strawberry.enum
class Resolution(Enum):
    RAW = "raw"
    MINUTE = "minute"


@strawberry.enum
class AlertErrorCode(Enum):
    NOT_FOUND = "NOT_FOUND"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"


# --- Tablero -------------------------------------------------------------------------------


@strawberry.type
class Vital:
    key: str
    label: str
    value: float
    unit: str
    domain: str
    severity: Severity
    evidence_state: EvidenceState
    origin: DataOrigin
    zone_id: strawberry.ID | None


@strawberry.type
class DashboardView:
    habitat_id: strawberry.ID
    global_severity: Severity
    vitals: list[Vital]


# --- Conocimiento --------------------------------------------------------------------------


@strawberry.type(name="Citation")
class CitationType:
    document_code: str
    requirement_ref: str | None
    page: int | None
    excerpt: str
    evidence_state: EvidenceState

    @staticmethod
    def of(c: knowledge.Citation | CitationDTO) -> CitationType:
        return CitationType(
            document_code=c.document_code,
            requirement_ref=c.requirement_ref,
            page=c.page,
            excerpt=c.excerpt,
            evidence_state=EvidenceState(str(c.evidence_state)),
        )


@strawberry.type(name="Action")
class ActionType:
    key: str
    title: str
    description: str


@strawberry.type(name="Recommendation")
class RecommendationType:
    id: strawberry.ID
    alert_id: strawberry.ID
    rule_key: str
    source_kind: EvidenceState
    body: str
    actions: list[ActionType]
    citations: list[CitationType]

    @staticmethod
    def of(r: knowledge.Recommendation) -> RecommendationType:
        return RecommendationType(
            id=strawberry.ID(str(r.id)),
            alert_id=strawberry.ID(str(r.alert_id)),
            rule_key=r.rule_key,
            source_kind=EvidenceState(r.source_kind),
            body=r.body,
            actions=[
                ActionType(key=a.key, title=a.title, description=a.description) for a in r.actions
            ],
            citations=[CitationType.of(c) for c in r.citations],
        )


# --- Monitoreo -----------------------------------------------------------------------------


@strawberry.type(name="Rule")
class RuleType:
    key: str
    parameter: str
    severity: Severity
    source_requirement: str
    source_document: str
    evidence_state: EvidenceState
    action_key: str
    hrp_hazard: str

    @staticmethod
    def of(r: RuleView) -> RuleType:
        return RuleType(
            key=r.key,
            parameter=r.parameter,
            severity=Severity(r.severity),
            source_requirement=r.source_requirement,
            source_document=r.source_document,
            evidence_state=EvidenceState(r.evidence_state),
            action_key=r.action_key,
            hrp_hazard=r.hrp_hazard,
        )


@strawberry.type(name="Alert")
class AlertType:
    id: strawberry.ID
    rule_key: str
    habitat_id: strawberry.ID
    zone_id: strawberry.ID | None
    severity: Severity
    status: AlertStatus
    cause_hint: str | None
    evidence_state: EvidenceState
    evidence: JSON
    raised_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None

    @strawberry.field
    def rule(self, info: GqlInfo) -> RuleType | None:
        view = info.context.services.rules.get(self.rule_key)
        return RuleType.of(view) if view else None

    @strawberry.field
    def recommendation(self, info: GqlInfo) -> RecommendationType | None:
        found = info.context.services.recommendation_for(UUID(self.id))
        return RecommendationType.of(found) if found else None

    @staticmethod
    def of(a: AlertView) -> AlertType:
        return AlertType(
            id=strawberry.ID(str(a.alert_id)),
            rule_key=a.rule_key,
            habitat_id=strawberry.ID(str(a.habitat_id)),
            zone_id=strawberry.ID(str(a.zone_id)) if a.zone_id else None,
            severity=Severity(a.severity),
            status=AlertStatus(a.status),
            cause_hint=a.cause_hint,
            evidence_state=EvidenceState(a.evidence_state),
            evidence=cast(JSON, a.evidence),
            raised_at=a.raised_at,
            acknowledged_at=a.acknowledged_at,
            resolved_at=a.resolved_at,
        )


@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor: str | None


@strawberry.type
class AlertConnection:
    nodes: list[AlertType]
    page_info: PageInfo


@strawberry.type
class AlertAcknowledgedPayload:
    alert: AlertType
    already_acknowledged: bool


@strawberry.type
class AlertError:
    code: AlertErrorCode
    message: str


AcknowledgeAlertResult = Annotated[
    AlertAcknowledgedPayload | AlertError, strawberry.union("AcknowledgeAlertResult")
]


# --- Telemetría ----------------------------------------------------------------------------


@strawberry.type(name="OutboxStats")
class OutboxStatsType:
    pending: int
    dead: int
    oldest_pending_age_s: float | None


@strawberry.type
class ReadingPoint:
    ts: datetime
    avg: float
    min: float
    max: float


@strawberry.type
class ReadingSeries:
    metric: str
    unit: str
    points: list[ReadingPoint]


# --- Utilidades ----------------------------------------------------------------------------


def _habitat(value: str) -> UUID:
    """Un hábitat se puede pedir por su UUID o por su código (`nave-transito`)."""
    try:
        return UUID(value)
    except ValueError:
        return habitat_id_of(value)


def _cursor(a: AlertView) -> str:
    return base64.urlsafe_b64encode(f"{a.raised_at.isoformat()}|{a.alert_id}".encode()).decode()


def _uncursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    at, _, alert_id = raw.partition("|")
    return datetime.fromisoformat(at), UUID(alert_id)


def _uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None


# --- Raíces --------------------------------------------------------------------------------


@strawberry.type
class Query:
    @strawberry.field
    async def dashboard(self, info: GqlInfo, habitat_id: strawberry.ID) -> DashboardView:
        services = info.context.services
        habitat = _habitat(habitat_id)
        latest = await services.telemetry.latest(habitat)
        alerts = await services.active_alerts.list(habitat_id=habitat)
        rules = {r.key: r for r in services.rules.all()}
        severity, vitals = build_dashboard(latest, alerts, rules)
        return DashboardView(
            habitat_id=strawberry.ID(str(habitat)),
            global_severity=Severity(severity),
            vitals=[
                Vital(
                    key=v.key,
                    label=v.label,
                    value=v.value,
                    unit=v.unit,
                    domain=v.domain,
                    severity=Severity(v.severity),
                    evidence_state=EvidenceState(v.evidence_state),
                    origin=DataOrigin(v.origin),
                    zone_id=strawberry.ID(str(v.zone_id)) if v.zone_id else None,
                )
                for v in vitals
            ],
        )

    @strawberry.field
    async def alerts(
        self,
        info: GqlInfo,
        first: int = 20,
        after: str | None = None,
        status: AlertStatus | None = None,
    ) -> AlertConnection:
        nodes, more = await info.context.services.alerts.page(
            max(1, min(first, MAX_PAGE)),
            after=_uncursor(after) if after else None,
            status=status.value if status else None,
        )
        return AlertConnection(
            nodes=[AlertType.of(a) for a in nodes],
            page_info=PageInfo(
                has_next_page=more, end_cursor=_cursor(nodes[-1]) if nodes else None
            ),
        )

    @strawberry.field
    async def alert(self, info: GqlInfo, id: strawberry.ID) -> AlertType | None:
        alert_id = _uuid_or_none(id)
        view = await info.context.services.alerts.get(alert_id) if alert_id else None
        return AlertType.of(view) if view else None

    @strawberry.field
    def rules(self, info: GqlInfo) -> list[RuleType]:
        return [RuleType.of(r) for r in info.context.services.rules.all()]

    @strawberry.field
    async def zone_readings(
        self,
        info: GqlInfo,
        zone_id: strawberry.ID,
        metrics: list[str],
        from_: Annotated[datetime, strawberry.argument(name="from")],
        to: datetime,
        resolution: Resolution = Resolution.MINUTE,
    ) -> list[ReadingSeries]:
        series = await info.context.services.telemetry.series(
            UUID(zone_id), metrics, from_, to, raw=resolution is Resolution.RAW
        )
        return [
            ReadingSeries(
                metric=s.metric,
                unit=s.unit,
                points=[ReadingPoint(ts=p.ts, avg=p.avg, min=p.min, max=p.max) for p in s.points],
            )
            for s in series
        ]

    # Estado del outbox. Solo en perfiles de desarrollo; en `jurado` devuelve null.
    @strawberry.field
    async def outbox_stats(self, info: GqlInfo) -> OutboxStatsType | None:
        read = info.context.services.outbox_stats
        if read is None:
            return None
        stats = await read()
        return OutboxStatsType(
            pending=stats.pending, dead=stats.dead, oldest_pending_age_s=stats.oldest_pending_age_s
        )

    @strawberry.field
    def knowledge_search(self, info: GqlInfo, query: str, k: int = 5) -> list[CitationType]:
        found = info.context.services.knowledge.search(query, max(1, min(k, 20)))
        return [CitationType.of(c) for c in found]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def acknowledge_alert(
        self, info: GqlInfo, id: strawberry.ID, note: str | None = None
    ) -> AcknowledgeAlertResult:
        services = info.context.services
        alert_id = _uuid_or_none(id)
        if alert_id is None:
            return AlertError(code=AlertErrorCode.NOT_FOUND, message=f"no existe la alerta {id}")
        result = await services.acknowledge(alert_id, note)
        if isinstance(result, AlertNotFound):
            return AlertError(code=AlertErrorCode.NOT_FOUND, message=f"no existe la alerta {id}")
        if isinstance(result, AlertAlreadyResolved):
            return AlertError(
                code=AlertErrorCode.ALREADY_RESOLVED, message="la alerta ya está resuelta"
            )
        view = await services.alerts.get(alert_id)
        assert view is not None  # se acaba de reconocer en la misma base
        return AlertAcknowledgedPayload(
            alert=AlertType.of(view), already_acknowledged=isinstance(result, AlreadyAcknowledged)
        )


schema = strawberry.Schema(
    query=Query, mutation=Mutation, extensions=[lambda: QueryDepthLimiter(max_depth=MAX_DEPTH)]
)
