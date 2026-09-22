import pytest
from starlette.testclient import TestClient

from apps.backend.main import create_app
from core.contracts.errors import ErrorCode


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Route config, lock, secrets, and DB to tmp_path
    monkeypatch.setattr("core.config.manager.DEFAULT_CONFIG_PATH", tmp_path / "config.yaml")
    monkeypatch.setattr("core.persistence.database.DEFAULT_DB_PATH", tmp_path / "oximoron.db")
    monkeypatch.setattr("core.supervisor.lock.DEFAULT_LOCK_PATH", tmp_path / "run" / ".supervisor.lock")
    monkeypatch.setattr("core.supervisor.lock.DEFAULT_DISCOVERY_PATH", tmp_path / "run" / "discovery.json")
    monkeypatch.setattr("core.secrets.manager.DEFAULT_CREDENTIAL_PATH", tmp_path / "run" / "credentials.json")

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

def test_unauthenticated_request_fails(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == ErrorCode.UNAUTHORIZED

def test_authenticated_health_request_succeeds(client):
    token = client.app.state.api_token
    response = client.get(
        "/api/v1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["protocol_version"] == "1.0.0"

def test_status_endpoint_returns_real_summary(client):
    token = client.app.state.api_token
    response = client.get(
        "/api/v1/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "cpu_percent" in data
    assert "ram_used_gb" in data

def test_cross_origin_rejection(client):
    token = client.app.state.api_token
    # Hostile origin
    response = client.get(
        "/api/v1/health",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://evil-tracker.com",
        },
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == ErrorCode.FORBIDDEN_ORIGIN

def test_allowed_tauri_origin(client):
    token = client.app.state.api_token
    response = client.get(
        "/api/v1/health",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "tauri://localhost",
        },
    )
    assert response.status_code == 200

def test_websocket_ticket_generation_and_consumption(client):
    token = client.app.state.api_token
    # 1. Request ticket
    resp = client.post(
        "/api/v1/events/ticket",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    ticket = resp.json()["ticket"]
    assert ticket

    # 2. Connect to WebSocket with ticket
    with client.websocket_connect("/api/v1/events") as ws:
        ws.send_text(ticket)
        data = ws.receive_json()
        assert data.get("type") == "connection.ready"
