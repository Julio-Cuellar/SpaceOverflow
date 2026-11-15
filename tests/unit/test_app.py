from fastapi.testclient import TestClient

from spaceapp.main import create_app
from spaceapp.platform.config import Settings
from spaceapp.platform.profiles import Profile


def test_health_reports_ok_and_the_active_profile():
    app = create_app(Settings(profile=Profile.DEV1))
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "profile": "dev1"}
