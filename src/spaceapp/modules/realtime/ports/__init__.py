"""Realtime gateway ports."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from spaceapp.modules.realtime.domain.messages import WsMessage


class OutboxReplay(Protocol):
    """Messages already emitted with `seq` greater than `after_id`, in order (24 h retention)."""

    async def after(self, after_id: int, limit: int) -> Sequence[WsMessage]: ...
