"""Repositorio del Enlace con Tierra sobre PostgreSQL. Trabaja en la transacción recibida."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from spaceapp.modules.groundlink.domain.plans import DraftItem
from spaceapp.modules.groundlink.ports import GroundPlanRow, LinkState

_PLAN = "SELECT id, version, status, batch_id, reason, published_at, acked_at FROM groundlink.ground_plan"
_ITEM_FIELDS = ("change", "kind", "title", "recurrence", "zone_code", "target_template_id")


class SqlGroundlinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # --- nave ----------------------------------------------------------------------------

    async def last_inbound_version(self) -> int | None:
        value = (
            await self._s.execute(
                text(
                    "SELECT max(plan_version) FROM groundlink.inbound_plan WHERE status <> 'RECHAZADO'"
                )
            )
        ).scalar_one()
        return int(value) if value is not None else None

    async def save_inbound(
        self,
        *,
        batch_id: UUID,
        plan_version: int,
        status: str,
        payload_hash: str,
        reason: str | None,
        at: datetime,
    ) -> bool:
        row = (
            await self._s.execute(
                text(
                    "INSERT INTO groundlink.inbound_plan (id, batch_id, plan_version, status, "
                    "payload_hash, reason, received_at) VALUES (:id, :b, :v, :s, :h, :r, :t) "
                    # Un lote rechazado (corrupto) se puede reenviar corregido con el mismo id.
                    "ON CONFLICT (batch_id) DO UPDATE SET plan_version = EXCLUDED.plan_version, "
                    "status = EXCLUDED.status, payload_hash = EXCLUDED.payload_hash, "
                    "reason = EXCLUDED.reason, received_at = EXCLUDED.received_at "
                    "WHERE groundlink.inbound_plan.status = 'RECHAZADO' RETURNING id"
                ),
                {
                    "id": uuid4(),
                    "b": batch_id,
                    "v": plan_version,
                    "s": status,
                    "h": payload_hash,
                    "r": reason,
                    "t": at,
                },
            )
        ).first()
        return row is not None

    async def mark_inbound_applied(
        self, plan_version: int, rejected: Sequence[dict[str, Any]], at: datetime
    ) -> UUID | None:
        batch = (
            await self._s.execute(
                text(
                    "UPDATE groundlink.inbound_plan SET status = 'APLICADO', applied_at = :t, "
                    "rejected = CAST(:r AS jsonb) WHERE plan_version = :v AND status <> 'RECHAZADO' "
                    "RETURNING batch_id"
                ),
                {"t": at, "r": json.dumps(list(rejected), ensure_ascii=False), "v": plan_version},
            )
        ).scalar_one_or_none()
        return batch if isinstance(batch, UUID) else None

    # --- Tierra --------------------------------------------------------------------------

    async def link(self) -> LinkState:
        await self._s.execute(
            text("INSERT INTO groundlink.link_state (id) VALUES (1) ON CONFLICT DO NOTHING")
        )
        row = (
            await self._s.execute(
                text("SELECT online, delay_s, changed_at FROM groundlink.link_state WHERE id = 1")
            )
        ).one()
        return LinkState(bool(row[0]), float(row[1]), row[2])

    async def set_link(self, online: bool, delay_s: float, at: datetime) -> None:
        await self._s.execute(
            text(
                "INSERT INTO groundlink.link_state (id, online, delay_s, changed_at) "
                "VALUES (1, :o, :d, :t) ON CONFLICT (id) DO UPDATE SET online = EXCLUDED.online, "
                "delay_s = EXCLUDED.delay_s, changed_at = EXCLUDED.changed_at"
            ),
            {"o": online, "d": delay_s, "t": at},
        )

    async def max_version(self) -> int:
        value = (
            await self._s.execute(
                text(
                    "SELECT greatest((SELECT max(version) FROM groundlink.ground_plan), "
                    "(SELECT max(plan_version) FROM groundlink.inbound_plan), 0)"
                )
            )
        ).scalar_one()
        return int(value)

    async def draft(self) -> GroundPlanRow | None:
        row = (await self._s.execute(text(_PLAN + " WHERE status = 'BORRADOR'"))).first()
        return GroundPlanRow(*row) if row else None

    async def create_draft(self, plan_id: UUID, version: int) -> None:
        await self._s.execute(
            text("INSERT INTO groundlink.ground_plan (id, version) VALUES (:id, :v)"),
            {"id": plan_id, "v": version},
        )

    async def plans(self, statuses: Sequence[str] | None = None) -> list[GroundPlanRow]:
        sql, params = _PLAN, {}
        if statuses is not None:
            sql += " WHERE status = ANY(CAST(:s AS text[]))"
            params = {"s": list(statuses)}
        rows = await self._s.execute(text(sql + " ORDER BY version"), params)
        return [GroundPlanRow(*r) for r in rows]

    async def plan(self, plan_id: UUID, *, lock: bool = False) -> GroundPlanRow | None:
        sql = _PLAN + " WHERE id = :i" + (" FOR UPDATE" if lock else "")
        row = (await self._s.execute(text(sql), {"i": plan_id})).first()
        return GroundPlanRow(*row) if row else None

    async def plan_by_batch(self, batch_id: UUID) -> GroundPlanRow | None:
        row = (
            await self._s.execute(text(_PLAN + " WHERE batch_id = :b FOR UPDATE"), {"b": batch_id})
        ).first()
        return GroundPlanRow(*row) if row else None

    async def items(self, plan_id: UUID) -> list[DraftItem]:
        rows = await self._s.execute(
            text(
                "SELECT change, target_template_id, title, kind FROM groundlink.ground_item "
                "WHERE plan_id = :p ORDER BY position"
            ),
            {"p": plan_id},
        )
        return [DraftItem(*r) for r in rows]

    async def item_dicts(self, plan_id: UUID) -> list[dict[str, Any]]:
        """Los ítems tal como viajan por el enlace (sin los campos vacíos)."""
        rows = await self._s.execute(
            text(
                f"SELECT {', '.join(_ITEM_FIELDS)} FROM groundlink.ground_item "
                "WHERE plan_id = :p ORDER BY position"
            ),
            {"p": plan_id},
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            item = {k: v for k, v in zip(_ITEM_FIELDS, r, strict=True) if v is not None}
            item["target_template_id"] = str(item["target_template_id"])
            out.append(item)
        return out

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
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO groundlink.ground_item (id, plan_id, position, change, "
                "target_template_id, kind, title, recurrence, zone_code) VALUES (:id, :p, "
                "(SELECT coalesce(max(position), 0) + 1 FROM groundlink.ground_item WHERE plan_id = :p), "
                ":c, :t, :k, :ti, :r, :z) ON CONFLICT (plan_id, target_template_id) DO UPDATE SET "
                "change = EXCLUDED.change, kind = EXCLUDED.kind, title = EXCLUDED.title, "
                "recurrence = EXCLUDED.recurrence, zone_code = EXCLUDED.zone_code"
            ),
            {
                "id": uuid4(),
                "p": plan_id,
                "c": change,
                "t": template_id,
                "k": kind,
                "ti": title,
                "r": recurrence,
                "z": zone_code,
            },
        )

    async def delete_item(self, plan_id: UUID, template_id: UUID) -> None:
        await self._s.execute(
            text(
                "DELETE FROM groundlink.ground_item WHERE plan_id = :p AND target_template_id = :t"
            ),
            {"p": plan_id, "t": template_id},
        )

    async def set_status(
        self,
        plan_id: UUID,
        status: str,
        *,
        only_from: Sequence[str] | None = None,
        batch_id: UUID | None = None,
        reason: str | None = None,
        at: datetime | None = None,
    ) -> bool:
        sets = ["status = :s"]
        params: dict[str, Any] = {"s": status, "i": plan_id}
        if batch_id is not None:
            sets.append("batch_id = :b")
            params["b"] = batch_id
        if reason is not None:
            sets.append("reason = :r")
            params["r"] = reason
        if at is not None:
            column = "acked_at" if status == "CONFIRMADO" else "published_at"
            sets.append(f"{column} = :t")
            params["t"] = at
        sql = f"UPDATE groundlink.ground_plan SET {', '.join(sets)} WHERE id = :i"
        if only_from is not None:
            sql += " AND status = ANY(CAST(:f AS text[]))"
            params["f"] = list(only_from)
        result = await self._s.execute(text(sql + " RETURNING id"), params)
        return result.first() is not None
