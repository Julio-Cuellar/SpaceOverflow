"""Puertos del gateway en tiempo real."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from spaceapp.modules.realtime.domain.messages import WsMessage


class OutboxReplay(Protocol):
    """Mensajes ya emitidos con `seq` mayor que `after_id`, en orden (retención de 24 h)."""

    async def after(self, after_id: int, limit: int) -> Sequence[WsMessage]: ...
