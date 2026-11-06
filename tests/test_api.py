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

# Security Test 7: Dashboard index sets HttpOnly session cookie and SameSite=Strict
def test_dashboard_cookie_security_flags():
    response = client.get("/")
    assert response.status_code == 200
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "artemis_session_token" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=strict" in set_cookie_header.lower()
    assert "artemis_csrf_token" in set_cookie_header

# Security Test 8: Removed endpoint /api/auth/token returns 404
def test_auth_token_endpoint_removed():
    response = client.get("/api/auth/token")
    assert response.status_code == 404

# Security Test 9: Valid cookie-authenticated request with CSRF token succeeds
def test_cookie_auth_with_valid_csrf():
    csrf_secret = "test_csrf_token_secret_12345"
    client.cookies.set("artemis_session_token", LOCAL_API_TOKEN)
    client.cookies.set("artemis_csrf_token", csrf_secret)
    
    response = client.post(
        "/api/stop",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "X-CSRF-Token": csrf_secret
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    # Clean client cookies after test
    client.cookies.clear()

# Security Test 10: Cookie auth with missing or mismatched CSRF token is rejected (403 Forbidden)
def test_cookie_auth_missing_or_invalid_csrf_blocked():
    client.cookies.set("artemis_session_token", LOCAL_API_TOKEN)
    client.cookies.set("artemis_csrf_token", "real_csrf_cookie_val")

    # Missing X-CSRF-Token header
    res1 = client.post(
        "/api/stop",
        headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert res1.status_code == 403
    assert "csrf token" in res1.json()["detail"].lower()

    # Mismatched X-CSRF-Token header
    res2 = client.post(
        "/api/stop",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "X-CSRF-Token": "attacker_fake_csrf"
        }
    )
    assert res2.status_code == 403
    assert "csrf token" in res2.json()["detail"].lower()
    client.cookies.clear()



