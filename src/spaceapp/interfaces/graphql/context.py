"""Contexto de cada operación GraphQL: los servicios que arma el composition root."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from strawberry.fastapi import BaseContext

from spaceapp.modules.engagement.application.service import EngagementService
from spaceapp.modules.engagement.facade import TaskQuery
from spaceapp.modules.facility.application.service import FacilityService
from spaceapp.modules.facility.facade import IncidentQuery, ShipQuery
from spaceapp.modules.groundlink.application.ground import GroundControl
from spaceapp.modules.knowledge.domain.model import Recommendation
from spaceapp.modules.knowledge.facade import KnowledgeQuery
from spaceapp.modules.monitoring.application.acknowledge_alert import AckResult
from spaceapp.modules.monitoring.facade import ActiveAlertsQuery, AlertReadQuery, RuleQuery
from spaceapp.modules.telemetry.facade import TelemetryViews
from spaceapp.platform.outbox import OutboxStats


@dataclass(frozen=True)
class Services:
    alerts: AlertReadQuery
    active_alerts: ActiveAlertsQuery
    rules: RuleQuery
    telemetry: TelemetryViews
    knowledge: KnowledgeQuery
    recommendation_for: Callable[[UUID], Recommendation | None]
    acknowledge: Callable[[UUID, str | None], Awaitable[AckResult]]
    facility: FacilityService
    ship: ShipQuery
    incidents: IncidentQuery
    engagement: EngagementService
    tasks: TaskQuery
    ground: GroundControl
    # Quién firma las acciones hasta que exista la selección de perfil.
    crew_member: UUID
    # Solo en los perfiles de desarrollo; en `jurado` es None y la consulta devuelve null.
    outbox_stats: Callable[[], Awaitable[OutboxStats]] | None = None


class Context(BaseContext):
    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
