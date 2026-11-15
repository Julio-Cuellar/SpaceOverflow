"""Fragmento GraphQL de Nave e incidencias: plano, tickets y catálogo de tipos."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, cast
from uuid import UUID

import strawberry
from strawberry.scalars import JSON

from spaceapp.interfaces.graphql.common import (
    DEFAULT_HABITAT,
    EvidenceState,
    GqlInfo,
    PageInfo,
    Severity,
    decode_cursor,
    encode_cursor,
    habitat,
    page_size,
    uuid_or_none,
)
from spaceapp.modules.facility.application.service import Done, Outcome
from spaceapp.modules.facility.domain.catalog import IncidentType as IncidentTypeData
from spaceapp.modules.facility.facade import IncidentUpdateView, IncidentView, ZoneView


@strawberry.enum
class IncidentStatus(Enum):
    ABIERTA = "abierta"
    RECONOCIDA = "reconocida"
    RESUELTA = "resuelta"


@strawberry.enum
class IncidentSource(Enum):
    ALERTA = "ALERTA"
    MANUAL = "MANUAL"


@strawberry.enum
class Detection(Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


@strawberry.enum
class IncidentErrorCode(Enum):
    NOT_FOUND = "NOT_FOUND"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"
    ACTIVE_ALERTS = "ACTIVE_ALERTS"
    UNKNOWN_ZONE = "UNKNOWN_ZONE"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    INVALID_SEVERITY = "INVALID_SEVERITY"


@strawberry.type
class ZoneLayout:
    x: float
    y: float
    w: float
    h: float


@strawberry.type
class Zone:
    id: strawberry.ID
    code: str
    name: str
    kind: str
    deck: int
    layout: ZoneLayout
    status: Severity
    open_incidents: int

    @staticmethod
    def of(z: ZoneView) -> Zone:
        return Zone(
            id=strawberry.ID(str(z.id)),
            code=z.code,
            name=z.name,
            kind=z.kind,
            deck=z.deck,
            layout=ZoneLayout(**{k: float(z.layout[k]) for k in ("x", "y", "w", "h")}),
            status=Severity(z.status),
            open_incidents=z.open_incidents,
        )


@strawberry.type
class Ship:
    habitat_id: strawberry.ID
    code: str
    name: str
    kind: str
    canvas: JSON | None
    zones: list[Zone]


@strawberry.type(name="IncidentType")
class IncidentTypeType:
    key: str
    category: str
    category_name: str
    name: str
    detection: Detection
    rule_keys: list[str]
    default_severity: Severity
    evidence_state: EvidenceState
    typical_zones: list[str]
    suggested_actions: list[str]

    @staticmethod
    def of(t: IncidentTypeData, category_name: str) -> IncidentTypeType:
        return IncidentTypeType(
            key=t.key,
            category=t.category,
            category_name=category_name,
            name=t.name,
            detection=Detection(t.detection),
            rule_keys=list(t.rule_keys),
            default_severity=Severity(t.default_severity),
            evidence_state=EvidenceState(t.evidence_state),
            typical_zones=list(t.typical_zones),
            suggested_actions=list(t.suggested_actions),
        )


@strawberry.type
class IncidentUpdate:
    kind: str
    note: str | None
    author_id: strawberry.ID | None
    at: datetime

    @staticmethod
    def of(u: IncidentUpdateView) -> IncidentUpdate:
        author = strawberry.ID(str(u.author_id)) if u.author_id else None
        return IncidentUpdate(kind=u.kind, note=u.note, author_id=author, at=u.at)


@strawberry.type
class Incident:
    id: strawberry.ID
    code: str
    habitat_id: strawberry.ID
    zone_id: strawberry.ID
    type_key: str
    source: IncidentSource
    source_alert_id: strawberry.ID | None
    title: str
    description: str
    severity: Severity
    status: IncidentStatus
    opened_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    values_normal: bool

    @strawberry.field
    def type(self, info: GqlInfo) -> IncidentTypeType | None:
        catalog = info.context.services.facility.catalog
        found = catalog.get(self.type_key)
        return IncidentTypeType.of(found, catalog.categories[found.category]) if found else None

    @strawberry.field
    async def updates(self, info: GqlInfo) -> list[IncidentUpdate]:
        rows = await info.context.services.incidents.updates(UUID(self.id))
        return [IncidentUpdate.of(u) for u in rows]

    @staticmethod
    def of(i: IncidentView) -> Incident:
        return Incident(
            id=strawberry.ID(str(i.id)),
            code=i.code,
            habitat_id=strawberry.ID(str(i.habitat_id)),
            zone_id=strawberry.ID(str(i.zone_id)),
            type_key=i.type_key,
            source=IncidentSource(i.source),
            source_alert_id=strawberry.ID(str(i.source_alert_id)) if i.source_alert_id else None,
            title=i.title,
            description=i.description,
            severity=Severity(i.severity),
            status=IncidentStatus(i.status),
            opened_at=i.opened_at,
            acknowledged_at=i.acknowledged_at,
            resolved_at=i.resolved_at,
            values_normal=i.values_normal_at is not None,
        )


@strawberry.type
class IncidentConnection:
    nodes: list[Incident]
    page_info: PageInfo


@strawberry.type
class IncidentPayload:
    incident: Incident
    already_done: bool


@strawberry.type
class IncidentError:
    code: IncidentErrorCode
    message: str


IncidentResult = Annotated[IncidentPayload | IncidentError, strawberry.union("IncidentResult")]


async def _result(info: GqlInfo, outcome: Outcome) -> IncidentPayload | IncidentError:
    if not isinstance(outcome, Done):
        return IncidentError(code=IncidentErrorCode(outcome.code), message=outcome.message)
    view = await info.context.services.incidents.get(outcome.incident_id)
    assert view is not None  # se acaba de escribir en la misma base
    return IncidentPayload(incident=Incident.of(view), already_done=outcome.already)


def _not_found(value: str) -> IncidentError:
    return IncidentError(code=IncidentErrorCode.NOT_FOUND, message=f"no existe {value}")


@strawberry.type
class FacilityQuery:
    @strawberry.field
    async def ship(self, info: GqlInfo, habitat_id: strawberry.ID | None = None) -> Ship | None:
        services = info.context.services
        await services.facility.ensure_ready()
        plan = services.facility.plan
        wanted = habitat(habitat_id or DEFAULT_HABITAT)
        if wanted != plan.habitat_id:
            return None
        zones = await services.ship.zones(plan.habitat_id)
        return Ship(
            habitat_id=strawberry.ID(str(plan.habitat_id)),
            code=plan.habitat_code,
            name=plan.habitat_name,
            kind=plan.habitat_kind,
            canvas=cast(JSON, plan.canvas),
            zones=[Zone.of(z) for z in zones],
        )

    @strawberry.field
    async def incidents(
        self,
        info: GqlInfo,
        first: int = 20,
        after: str | None = None,
        status: IncidentStatus | None = None,
        zone_id: strawberry.ID | None = None,
    ) -> IncidentConnection:
        zone = uuid_or_none(zone_id) if zone_id else None
        if zone_id and zone is None:
            return IncidentConnection(
                nodes=[], page_info=PageInfo(has_next_page=False, end_cursor=None)
            )
        nodes, more = await info.context.services.incidents.page(
            page_size(first),
            after=decode_cursor(after) if after else None,
            status=status.value if status else None,
            zone_id=zone,
        )
        last = nodes[-1] if nodes else None
        return IncidentConnection(
            nodes=[Incident.of(i) for i in nodes],
            page_info=PageInfo(
                has_next_page=more,
                end_cursor=encode_cursor(last.opened_at, last.id) if last else None,
            ),
        )

    @strawberry.field
    async def incident(self, info: GqlInfo, id: strawberry.ID) -> Incident | None:
        incident_id = uuid_or_none(id)
        view = await info.context.services.incidents.get(incident_id) if incident_id else None
        return Incident.of(view) if view else None

    @strawberry.field
    def incident_types(self, info: GqlInfo, category: str | None = None) -> list[IncidentTypeType]:
        catalog = info.context.services.facility.catalog
        return [
            IncidentTypeType.of(t, catalog.categories[t.category])
            for t in catalog.types
            if category is None or t.category == category
        ]


@strawberry.type
class FacilityMutation:
    @strawberry.mutation
    async def report_incident(
        self,
        info: GqlInfo,
        zone_id: strawberry.ID,
        type_key: str,
        description: str | None = None,
        severity: Severity | None = None,
    ) -> IncidentResult:
        services = info.context.services
        zone = uuid_or_none(zone_id)
        if zone is None:
            return IncidentError(
                code=IncidentErrorCode.UNKNOWN_ZONE,
                message=f"la zona {zone_id} no está en el plano",
            )
        if severity is Severity.NORMAL:
            return IncidentError(
                code=IncidentErrorCode.INVALID_SEVERITY,
                message="un ticket es de Atención, Alerta o Crítico",
            )
        outcome = await services.facility.report(
            zone,
            type_key,
            services.crew_member,
            description=description,
            severity=severity.value if severity else None,
        )
        return await _result(info, outcome)

    @strawberry.mutation
    async def acknowledge_incident(self, info: GqlInfo, id: strawberry.ID) -> IncidentResult:
        incident_id = uuid_or_none(id)
        if incident_id is None:
            return _not_found(f"la incidencia {id}")
        services = info.context.services
        return await _result(
            info, await services.facility.acknowledge(incident_id, services.crew_member)
        )

    @strawberry.mutation
    async def resolve_incident(
        self, info: GqlInfo, id: strawberry.ID, note: str | None = None
    ) -> IncidentResult:
        incident_id = uuid_or_none(id)
        if incident_id is None:
            return _not_found(f"la incidencia {id}")
        services = info.context.services
        outcome = await services.facility.resolve(incident_id, services.crew_member, note)
        return await _result(info, outcome)
