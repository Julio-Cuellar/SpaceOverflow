"""Tipos y utilidades que comparten los fragmentos del esquema GraphQL."""

from __future__ import annotations

import base64
from datetime import datetime
from enum import Enum
from uuid import UUID

import strawberry
from strawberry import Info

from spaceapp.interfaces.graphql.context import Context
from spaceapp.platform.ids import habitat_id as habitat_id_of

MAX_PAGE = 100
DEFAULT_HABITAT = "nave-transito"

GqlInfo = Info[Context, None]


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


@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor: str | None


def habitat(value: str) -> UUID:
    """Un hábitat se puede pedir por su UUID o por su código (`nave-transito`)."""
    try:
        return UUID(value)
    except ValueError:
        return habitat_id_of(value)


def page_size(first: int) -> int:
    return max(1, min(first, MAX_PAGE))


def encode_cursor(at: datetime, item_id: UUID) -> str:
    return base64.urlsafe_b64encode(f"{at.isoformat()}|{item_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    at, _, item_id = raw.partition("|")
    return datetime.fromisoformat(at), UUID(item_id)


def uuid_or_none(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
