"""Casos de uso de Nave e incidencias: tickets desde alertas, reportes manuales y color de zonas.

Cada cambio de ticket o de zona y su evento se escriben en la misma transacción.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from spaceapp.modules.facility.contracts import (
    IncidentOpened,
    IncidentResolved,
    IncidentUpdated,
    ZoneStatusChanged,
)
from spaceapp.modules.facility.domain.catalog import IncidentCatalog
from spaceapp.modules.facility.domain.incidents import (
    OpenTicket,
    describe,
    on_alert,
    resolve_check,
    zone_status,
)
from spaceapp.modules.facility.domain.plan import Plan, PlannedZone
from spaceapp.modules.facility.ports import (
    ActiveAlertsSource,
    FacilityRepository,
    TicketRow,
    ZoneAlert,
)
from spaceapp.modules.monitoring.contracts import AlertRaised, AlertResolved
from spaceapp.platform.bus import HandlerContext
from spaceapp.platform.events import EventEnvelope, EventPayload
from spaceapp.platform.outbox import UnitOfWork

log = logging.getLogger(__name__)

CONSUMER_RAISED = "facility.on_alert_raised"
CONSUMER_RESOLVED = "facility.on_alert_resolved"
VALUES_NORMAL_NOTE = "Valores normales: el ticket puede cerrarse."

Publish = Callable[[EventEnvelope], Awaitable[None]]
RepositoryFactory = Callable[[AsyncSession], FacilityRepository]


# --- Resultados de las mutaciones ----------------------------------------------------------


@dataclass(frozen=True)
class Done:
    incident_id: UUID
    already: bool = False


@dataclass(frozen=True)
class Failed:
    code: str  # NOT_FOUND, ALREADY_RESOLVED, ACTIVE_ALERTS, UNKNOWN_ZONE, UNKNOWN_TYPE
    message: str


Outcome = Done | Failed


class FacilityService:
    def __init__(
        self,
        plan: Plan,
        catalog: IncidentCatalog,
        session_factory: async_sessionmaker[AsyncSession],
        repository: RepositoryFactory,
        active_alerts: ActiveAlertsSource,
    ) -> None:
        self.plan = plan
        self.catalog = catalog
        self._sf = session_factory
        self._repo = repository
        self._active_alerts = active_alerts
        self._ready = False

    # --- Arranque ------------------------------------------------------------------------

    async def ensure_ready(self) -> None:
        """Una vez por proceso: sincroniza el plano y reconstruye el estado de las zonas."""
        if not self._ready:
            await self.rebuild()
            self._ready = True

    async def rebuild(self) -> None:
        zones = {z.id for z in self.plan.zones}
        alerts = [a for a in await self._active_alerts(self.plan.habitat_id) if a.zone_id in zones]
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            await repo.ensure_plan(self.plan)
            await repo.replace_zone_alerts(sorted(zones), alerts)
            now = datetime.now(UTC)
            for zone in self.plan.zones:
                await self._refresh_zone(repo, zone, uow.publish, now)

    # --- Handlers del bus ----------------------------------------------------------------

    async def on_alert_raised(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        alert = event.payload_as(AlertRaised)
        zone = self.plan.zone_by_id(alert.zone_id) if alert.zone_id else None
        if zone is None:
            return  # alerta del cuerpo o de una zona que no está en el plano
        await self.ensure_ready()
        repo = self._repo(_session(ctx))
        at = event.occurred_at
        await repo.add_zone_alert(
            ZoneAlert(alert.alert_id, zone.id, alert.rule_key, alert.severity, at)
        )
        ticket = await repo.open_auto_ticket(zone.id)
        decision = on_alert(_open(ticket), alert.severity)
        incident_type = self.catalog.type_for_rule(alert.rule_key)
        title = incident_type.name if incident_type else alert.rule_key
        description = describe(title, zone.name, alert.evidence)
        if decision == "open":
            incident_id = uuid4()
            await repo.insert_ticket(
                incident_id=incident_id,
                habitat_id=self.plan.habitat_id,
                zone_id=zone.id,
                type_key=incident_type.key if incident_type else alert.rule_key,
                source="ALERTA",
                source_alert_id=alert.alert_id,
                reported_by=None,
                title=title,
                description=description,
                severity=alert.severity,
                at=at,
            )
            await repo.add_update(incident_id, "opened", description, None, at)
            await ctx.publish(
                self._event(
                    IncidentOpened(
                        incident_id=incident_id,
                        zone_id=zone.id,
                        severity=alert.severity,
                        title=title,
                        description=description,
                        source="ALERTA",
                    ),
                    incident_id,
                    cause=event,
                )
            )
        elif ticket is not None and decision in ("escalate", "note"):
            await repo.add_update(ticket.id, "alert", description, None, at)
            if decision == "escalate":
                await repo.set_severity(ticket.id, alert.severity)
                await ctx.publish(
                    self._event(
                        IncidentUpdated(
                            incident_id=ticket.id,
                            severity=alert.severity,
                            status=ticket.status,
                            note=description,
                        ),
                        ticket.id,
                        cause=event,
                    )
                )
        await self._refresh_zone(repo, zone, ctx.publish, at, cause=event)

    async def on_alert_resolved(self, event: EventEnvelope, ctx: HandlerContext) -> None:
        resolved = event.payload_as(AlertResolved)
        await self.ensure_ready()
        repo = self._repo(_session(ctx))
        zone_id = await repo.remove_zone_alert(resolved.alert_id)
        zone = self.plan.zone_by_id(zone_id) if zone_id else None
        if zone is None:
            return
        at = resolved.resolved_at
        ticket = await repo.open_auto_ticket(zone.id)
        if ticket is not None and not await repo.alert_severities(zone.id):
            # El ticket no se cierra solo: queda marcado para que la tripulación lo cierre.
            await repo.mark_values_normal(ticket.id, at)
            await repo.add_update(ticket.id, "values_normal", VALUES_NORMAL_NOTE, None, at)
            await ctx.publish(
                self._event(
                    IncidentUpdated(
                        incident_id=ticket.id,
                        severity=ticket.severity,
                        status=ticket.status,
                        note=VALUES_NORMAL_NOTE,
                    ),
                    ticket.id,
                    cause=event,
                )
            )
        await self._refresh_zone(repo, zone, ctx.publish, at, cause=event)

    # --- Mutaciones ----------------------------------------------------------------------

    async def report(
        self,
        zone_id: UUID,
        type_key: str,
        reporter: UUID,
        *,
        description: str | None = None,
        severity: str | None = None,
    ) -> Outcome:
        await self.ensure_ready()
        zone = self.plan.zone_by_id(zone_id)
        if zone is None:
            return Failed("UNKNOWN_ZONE", f"la zona {zone_id} no está en el plano")
        incident_type = self.catalog.get(type_key)
        if incident_type is None:
            return Failed("UNKNOWN_TYPE", f"no existe el tipo de incidencia {type_key!r}")
        sev = severity or incident_type.default_severity
        text = description or f"{incident_type.name} en {zone.name}."
        at = datetime.now(UTC)
        incident_id = uuid4()
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            await repo.insert_ticket(
                incident_id=incident_id,
                habitat_id=self.plan.habitat_id,
                zone_id=zone.id,
                type_key=incident_type.key,
                source="MANUAL",
                source_alert_id=None,
                reported_by=reporter,
                title=incident_type.name,
                description=text,
                severity=sev,
                at=at,
            )
            await repo.add_update(incident_id, "opened", text, reporter, at)
            await uow.publish(
                self._event(
                    IncidentOpened(
                        incident_id=incident_id,
                        zone_id=zone.id,
                        severity=sev,
                        title=incident_type.name,
                        description=text,
                        source="MANUAL",
                    ),
                    incident_id,
                )
            )
            await self._refresh_zone(repo, zone, uow.publish, at)
        return Done(incident_id)

    async def acknowledge(self, incident_id: UUID, crew_member: UUID) -> Outcome:
        at = datetime.now(UTC)
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            ticket = await repo.ticket(incident_id, lock=True)
            if ticket is None:
                return Failed("NOT_FOUND", f"no existe la incidencia {incident_id}")
            if ticket.status == "resuelta":
                return Failed("ALREADY_RESOLVED", "la incidencia ya está resuelta")
            if ticket.status == "reconocida":
                return Done(incident_id, already=True)
            await repo.set_status(incident_id, "reconocida", at)
            await repo.add_update(incident_id, "acknowledged", None, crew_member, at)
            await uow.publish(
                self._event(
                    IncidentUpdated(
                        incident_id=incident_id,
                        severity=ticket.severity,
                        status="reconocida",
                    ),
                    incident_id,
                )
            )
        return Done(incident_id)

    async def resolve(self, incident_id: UUID, crew_member: UUID, note: str | None) -> Outcome:
        at = datetime.now(UTC)
        async with UnitOfWork(self._sf) as uow:
            repo = self._repo(uow.session)
            ticket = await repo.ticket(incident_id, lock=True)
            if ticket is None:
                return Failed("NOT_FOUND", f"no existe la incidencia {incident_id}")
            active = len(await repo.alert_severities(ticket.zone_id))
            error = resolve_check(ticket.source, ticket.status, active_alerts=active)
            if error == "ALREADY_RESOLVED":
                return Failed(error, "la incidencia ya está resuelta")
            if error == "ACTIVE_ALERTS":
                return Failed(
                    error,
                    f"la zona tiene {active} alerta(s) activa(s): valores aún fuera de rango",
                )
            await repo.set_status(incident_id, "resuelta", at)
            await repo.add_update(incident_id, "resolved", note, crew_member, at)
            await uow.publish(
                self._event(
                    IncidentResolved(
                        incident_id=incident_id, zone_id=ticket.zone_id, resolved_at=at
                    ),
                    incident_id,
                )
            )
            zone = self.plan.zone_by_id(ticket.zone_id)
            if zone is not None:
                await self._refresh_zone(repo, zone, uow.publish, at)
        return Done(incident_id)

    # --- Apoyo ---------------------------------------------------------------------------

    async def _refresh_zone(
        self,
        repo: FacilityRepository,
        zone: PlannedZone,
        publish: Publish,
        at: datetime,
        *,
        cause: EventEnvelope | None = None,
    ) -> None:
        """Color de la zona: la peor severidad entre alertas activas y tickets abiertos."""
        current = await repo.zone_status(zone.id)
        tickets = await repo.open_ticket_severities(zone.id)
        status = zone_status(await repo.alert_severities(zone.id), tickets)
        if status == current:
            return
        await repo.set_zone_status(zone.id, status, at)
        await publish(
            self._event(
                ZoneStatusChanged(zone_id=zone.id, status=status, open_incidents=len(tickets)),
                zone.id,
                aggregate_type="zone",
                cause=cause,
            )
        )

    def _event(
        self,
        payload: EventPayload,
        aggregate_id: UUID,
        *,
        aggregate_type: str = "incident",
        cause: EventEnvelope | None = None,
    ) -> EventEnvelope:
        return EventEnvelope.from_payload(
            payload,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            partition_key=f"habitat:{self.plan.habitat_id}",
            correlation_id=(cause.correlation_id or cause.event_id) if cause else None,
            causation_id=cause.event_id if cause else None,
        )


def _session(ctx: HandlerContext) -> AsyncSession:
    if ctx.session is None:
        raise RuntimeError("Nave e incidencias necesita la sesión del relay del outbox")
    return ctx.session


def _open(ticket: TicketRow | None) -> OpenTicket | None:
    return OpenTicket(ticket.severity, ticket.source, ticket.status) if ticket else None
