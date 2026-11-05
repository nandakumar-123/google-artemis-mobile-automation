from app.adb_manager import ADBManager

def test_adb_manager_initialization():
    adb = ADBManager()
    assert adb.adb_bin is not None

def test_adb_version():
    adb = ADBManager()
    version_out = adb.get_version()
    assert "Android Debug Bridge" in version_out or "version" in version_out.lower()

def test_get_devices():
    adb = ADBManager()
    devices = adb.get_devices()
    assert isinstance(devices, list)
    # If device is connected, check fields
    for d in devices:
        assert "serial" in d
        assert "state" in d
        assert "type" in d

def test_check_connection_status():
    adb = ADBManager()
    status = adb.check_connection_status()
    assert "connected" in status
    assert "status" in status
    assert "connection_type" in status
    if status["connected"]:
        assert status["serial"] is not None

def test_device_selection():
    adb = ADBManager()
    assert adb.set_selected_device("192.168.1.50:5555") is True
    assert adb.selected_device == "192.168.1.50:5555"

def test_already_connected_pair_avoidance():
    adb = ADBManager()
    # Check if a device is active
    devices = [d for d in adb.get_devices() if d["state"] == "device"]
    if devices:
        serial = devices[0]["serial"]
        if ":" in serial:
            ip, port = serial.split(":", 1)
            success, msg = adb.pair_device(ip, int(port), "123456")
            assert success is True
            assert "already connected" in msg.lower()

def test_parse_qr_payload_standard_android():
    adb = ADBManager()
    payload = "WIFI:T:ADB;S:adb-device-1234;P:892341;;"
    parsed = adb.parse_qr_payload(payload, fallback_ip="192.168.137.5")
    assert parsed["type"] == "android_wifi_adb"
    assert parsed["service_name"] == "adb-device-1234"
    assert parsed["password"] == "892341"
    assert parsed["ip"] == "192.168.137.5"

def test_parse_qr_payload_json():
    adb = ADBManager()
    payload = '{"ip": "192.168.1.100", "port": 45123, "code": "654321"}'
    parsed = adb.parse_qr_payload(payload)
    assert parsed["type"] == "json"
    assert parsed["ip"] == "192.168.1.100"
    assert parsed["port"] == 45123
    assert parsed["password"] == "654321"

def test_parse_qr_payload_colon_separated():
    adb = ADBManager()
    payload = "192.168.1.10:39481:112233"
    parsed = adb.parse_qr_payload(payload)
    assert parsed["type"] == "colon_separated"
    assert parsed["ip"] == "192.168.1.10"
    assert parsed["port"] == 39481
    assert parsed["password"] == "112233"
