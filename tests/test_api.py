from fastapi.testclient import TestClient
from app.main import app
from app.config import LOCAL_API_TOKEN

client = TestClient(app)

AUTH_HEADERS = {
    "Origin": "http://127.0.0.1:8000",
    "X-API-Token": LOCAL_API_TOKEN
}

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
    response = client.post("/api/stop", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_wireless_disconnect_endpoint():
    response = client.post("/api/device/disconnect", json={}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "message" in data

def test_wireless_select_endpoint():
    response = client.post("/api/device/select", json={"serial": "emulator-5554"}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_qr_pair_endpoint_invalid_payload():
    response = client.post("/api/device/pair-qr", json={"qr_payload": "INVALID_TEXT"}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "missing" in data["message"].lower() or "failed" in data["message"].lower()

def test_qr_pair_endpoint_standard_format():
    payload = "WIFI:T:ADB;S:studio-device-test;P:123456;;"
    response = client.post("/api/device/pair-qr", json={"qr_payload": payload, "phone_ip": "192.168.137.20"}, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data

# Security Test 1: Missing Token
def test_missing_token_blocked():
    response = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert response.status_code == 401
    assert "missing or invalid" in response.json()["detail"].lower()

# Security Test 2: Invalid Token
def test_invalid_token_blocked():
    response = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000", "X-API-Token": "invalid_wrong_token_12345"}
    )
    assert response.status_code == 401
    assert "missing or invalid" in response.json()["detail"].lower()

# Security Test 3: Missing Origin / Referer
def test_missing_origin_and_referer_blocked():
    response = client.post(
        "/api/stop",
        headers={"X-API-Token": LOCAL_API_TOKEN}
    )
    assert response.status_code == 403
    assert "origin or referer header is required" in response.json()["detail"].lower()

# Security Test 4: Malicious Cross-Site Origin
def test_malicious_origin_blocked():
    response = client.post(
        "/api/stop",
        headers={"Origin": "https://malicious-attacker.com", "X-API-Token": LOCAL_API_TOKEN}
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"].lower()

# Security Test 5: Valid Local Token and Origin Allowed
def test_valid_token_and_origin_allowed():
    response = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000", "X-API-Token": LOCAL_API_TOKEN}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

# Security Test 6: Bearer authorization header accepted
def test_bearer_authorization_header_allowed():
    response = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000", "Authorization": f"Bearer {LOCAL_API_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


