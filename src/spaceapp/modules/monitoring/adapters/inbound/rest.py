"""GET /api/v1/rules/catalog.json: el catálogo con su fuente, versionado por ETag."""

import json
from dataclasses import asdict

from fastapi import APIRouter, Request, Response

from spaceapp.modules.monitoring.domain.rules import RuleCatalog


def build_router(catalog: RuleCatalog) -> APIRouter:
    router = APIRouter()
    body = json.dumps(
        {"version": catalog.version, "rules": [asdict(r) for r in catalog.rules]},
        ensure_ascii=False,
    ).encode("utf-8")
    etag = f'"{catalog.version}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=3600"}

    @router.get("/api/v1/rules/catalog.json")
    async def rules_catalog(request: Request) -> Response:
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(content=body, media_type="application/json", headers=headers)

    return router
