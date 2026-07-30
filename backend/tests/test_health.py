from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_root_health_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.health.check_database_connection", lambda: True)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "pharmaq-sentinel-api",
        "version": "0.1.0",
        "database": {"provider": "mysql", "status": "connected"},
    }


def test_api_v1_health_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.health.check_database_connection", lambda: True)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == {"provider": "mysql", "status": "connected"}


def test_database_connected_health_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.health.check_database_connection", lambda: True)

    response = client.get("/api/v1/health")

    assert response.json()["status"] == "healthy"
    assert response.json()["database"]["status"] == "connected"


def test_database_unavailable_health_response(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.health.check_database_connection", lambda: False)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == {"provider": "mysql", "status": "unavailable"}
