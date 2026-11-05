from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"

def test_device_status():
    response = client.get("/api/device/status")
    assert response.status_code == 200
    data = response.json()
    assert "connected" in data
    assert "status" in data
    assert "connection_type" in data
    assert "available_devices" in data

def test_get_history():
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_stop_endpoint():
    response = client.post("/api/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_wireless_disconnect_endpoint():
    response = client.post("/api/device/disconnect", json={})
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data

def test_wireless_select_endpoint():
    response = client.post("/api/device/select", json={"serial": "emulator-5554"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_qr_pair_endpoint_invalid_payload():
    response = client.post("/api/device/pair-qr", json={"qr_payload": "INVALID_TEXT"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "missing" in data["message"].lower() or "failed" in data["message"].lower()

def test_qr_pair_endpoint_standard_format():
    payload = "WIFI:T:ADB;S:studio-device-test;P:123456;;"
    response = client.post("/api/device/pair-qr", json={"qr_payload": payload, "phone_ip": "192.168.137.20"})
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

def test_unauthorized_cross_site_origin_blocked():
    # Verify CSRF/Origin security blocks cross-site attacks
    response = client.post(
        "/api/stop",
        headers={"Origin": "https://malicious-attacker.com"}
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()

def test_authorized_origin_allowed():
    # Verify local origin passes validation
    response = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

