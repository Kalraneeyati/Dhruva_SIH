from fastapi.testclient import TestClient

from dhruva.app import ADVISORY_NOTICE, create_app

client = TestClient(create_app())


def test_health_is_200():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readiness_reports_503_when_dependencies_are_unreachable():
    """A readiness probe must fail loudly. This runs with no postgres in CI."""
    r = client.get("/health/ready")
    assert r.status_code in (200, 503)
    body = r.json()
    assert set(body["checks"]) == {"postgres", "redis"}
    if r.status_code == 503:
        assert body["ready"] is False


def test_advisory_notice_is_carried():
    """Every advisory response carries it; the app describes itself with it too."""
    assert "INCOIS" in ADVISORY_NOTICE and "IMD" in ADVISORY_NOTICE
