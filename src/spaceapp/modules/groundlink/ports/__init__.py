"""Puertos del Enlace con Tierra."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from spaceapp.modules.groundlink.domain.plans import DraftItem, ShipTemplate


@dataclass(frozen=True)
class GroundPlanRow:
    id: UUID
    version: int
    status: str
    batch_id: UUID | None
    reason: str | None
    published_at: datetime | None
    acked_at: datetime | None


@dataclass(frozen=True)
class LinkState:
    online: bool
    delay_s: float
    changed_at: datetime


ShipTemplates = Callable[[], Awaitable[list[ShipTemplate]]]
# Programa una entrega por el enlace dentro de `delay_s` segundos.
Schedule = Callable[[float, Callable[[], Awaitable[None]]], None]


class GroundlinkRepository(Protocol):
    # --- nave ---
    async def last_inbound_version(self) -> int | None: ...

    async def save_inbound(
        self,
        *,
        batch_id: UUID,
        plan_version: int,
        status: str,
        payload_hash: str,
        reason: str | None,
        at: datetime,
    ) -> bool: ...

    async def mark_inbound_applied(
        self, plan_version: int, rejected: Sequence[dict[str, Any]], at: datetime
    ) -> UUID | None: ...

    # --- Tierra ---
    async def link(self) -> LinkState: ...

    async def set_link(self, online: bool, delay_s: float, at: datetime) -> None: ...

    async def max_version(self) -> int: ...

    async def draft(self) -> GroundPlanRow | None: ...

    async def create_draft(self, plan_id: UUID, version: int) -> None: ...

    async def plans(self, statuses: Sequence[str] | None = None) -> list[GroundPlanRow]: ...

    async def plan(self, plan_id: UUID, *, lock: bool = False) -> GroundPlanRow | None: ...

    async def plan_by_batch(self, batch_id: UUID) -> GroundPlanRow | None: ...

    async def items(self, plan_id: UUID) -> list[DraftItem]: ...

    async def item_dicts(self, plan_id: UUID) -> list[dict[str, Any]]: ...

    async def upsert_item(
        self,
        plan_id: UUID,
        *,
        change: str,
        template_id: UUID,
        kind: str | None,
        title: str | None,
        recurrence: str | None,
        zone_code: str | None,
    ) -> None: ...

    async def delete_item(self, plan_id: UUID, template_id: UUID) -> None: ...

    async def set_status(
        self,
        plan_id: UUID,
        status: str,
        *,
        only_from: Sequence[str] | None = None,
        batch_id: UUID | None = None,
        reason: str | None = None,
        at: datetime | None = None,
    ) -> bool: ...
