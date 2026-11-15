"""Contexto de cada operación GraphQL: los servicios que arma el composition root."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from strawberry.fastapi import BaseContext

from spaceapp.modules.knowledge.domain.model import Recommendation
from spaceapp.modules.knowledge.facade import KnowledgeQuery
from spaceapp.modules.monitoring.application.acknowledge_alert import AckResult
from spaceapp.modules.monitoring.facade import ActiveAlertsQuery, AlertReadQuery, RuleQuery
from spaceapp.modules.telemetry.facade import TelemetryViews


@dataclass(frozen=True)
class Services:
    alerts: AlertReadQuery
    active_alerts: ActiveAlertsQuery
    rules: RuleQuery
    telemetry: TelemetryViews
    knowledge: KnowledgeQuery
    recommendation_for: Callable[[UUID], Recommendation | None]
    acknowledge: Callable[[UUID, str | None], Awaitable[AckResult]]


class Context(BaseContext):
    def __init__(self, services: Services) -> None:
        super().__init__()
        self.services = services
