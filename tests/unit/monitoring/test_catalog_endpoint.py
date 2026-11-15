from fastapi.testclient import TestClient

from spaceapp.main import create_app
from spaceapp.platform.config import Settings


def test_the_rule_catalog_is_exposed_with_its_version_as_etag():
    with TestClient(create_app(Settings())) as client:
        r = client.get("/api/v1/rules/catalog.json")
        body = r.json()
        assert r.status_code == 200
        assert r.headers["etag"] == f'"{body["version"]}"'
        assert "max-age" in r.headers["cache-control"]
        assert len(body["rules"]) >= 20
        first = body["rules"][0]
        assert {"key", "evidence_state", "source_requirement", "source_document"} <= set(first)


def test_a_client_with_the_current_version_gets_304_without_a_body():
    with TestClient(create_app(Settings())) as client:
        etag = client.get("/api/v1/rules/catalog.json").headers["etag"]
        r = client.get("/api/v1/rules/catalog.json", headers={"If-None-Match": etag})
        assert r.status_code == 304 and r.content == b""
        other = client.get("/api/v1/rules/catalog.json", headers={"If-None-Match": '"old"'})
        assert other.status_code == 200
