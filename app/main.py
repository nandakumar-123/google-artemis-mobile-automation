import os
import hmac
import secrets
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_DIR, SCREENSHOTS_DIR, HOST, PORT, LOCAL_API_TOKEN
from app.device_controller import DeviceController
from app.database import init_db, get_task_history
from app.schemas import (
    ExecuteRequest, 
    ExecuteResponse, 
    ConfirmationRequest, 
    DeviceStatusResponse,
    PairRequest,
    ConnectRequest,
    DisconnectRequest,
    SelectDeviceRequest,
    QRPairRequest,
    WirelessResponse
)

app = FastAPI(title="Android AI Assistant", version="1.0.0")

ALLOWED_HOSTS = {
    "127.0.0.1",
    "localhost",
    f"127.0.0.1:{PORT}",
    f"localhost:{PORT}",
    f"{HOST}:{PORT}",
    HOST
}

# 1. CORS Configuration for local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        f"http://{HOST}:{PORT}"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_request_origin(request: Request):
    """
    Validates request origin and referer to prevent Cross-Site Request Forgery (CSRF).
    Rejects requests where both Origin and Referer headers are missing or invalid
    for browser-facing state-changing requests.
    """
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    sec_fetch_site = request.headers.get("sec-fetch-site")

    # Reject cross-site requests detected by browser Sec-Fetch-Site metadata
    if sec_fetch_site and sec_fetch_site == "cross-site":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Cross-site request blocked by origin policy."
        )

    # Require either Origin or Referer header
    if not origin and not referer:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Origin or Referer header is required for state-changing operations."
        )

    # Validate Origin header if present
    if origin:
        parsed_origin = urlparse(origin)
        netloc = parsed_origin.netloc.lower()
        hostname = parsed_origin.hostname.lower() if parsed_origin.hostname else ""
        if netloc not in ALLOWED_HOSTS and hostname not in ALLOWED_HOSTS:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Origin '{origin}' is not authorized."
            )

    # Validate Referer header if present
    if referer:
        parsed_ref = urlparse(referer)
        ref_netloc = parsed_ref.netloc.lower()
        ref_hostname = parsed_ref.hostname.lower() if parsed_ref.hostname else ""
        if ref_netloc not in ALLOWED_HOSTS and ref_hostname not in ALLOWED_HOSTS:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Referer '{referer}' is not authorized."
            )

    return True

def verify_api_token(request: Request):
    """
    Authenticates requests for sensitive device-control operations.
    Supports two secure authentication pathways:
    1. External clients: Header authentication via 'X-API-Token' or 'Authorization: Bearer <token>' matching LOCAL_API_TOKEN.
    2. Local dashboard: Cookie authentication via session cookie 'artemis_session_token' (which holds LOCAL_API_TOKEN)
       AND CSRF protection via 'artemis_csrf_token' cookie matching 'X-CSRF-Token' request header.
       If the session cookie is present and valid, and the request comes from the same local origin (127.0.0.1/localhost)
       with Sec-Fetch-Site != "cross-site", authenticate the browser session seamlessly.
    """
    # 1. External header token check
    header_token = request.headers.get("X-API-Token")
    if not header_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            header_token = auth_header[7:].strip()

    if header_token:
        if hmac.compare_digest(header_token, LOCAL_API_TOKEN):
            return "header"
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid API token."
        )

    # 2. Local browser session cookie + CSRF check
    session_cookie = request.cookies.get("artemis_session_token")
    if session_cookie:
        if not hmac.compare_digest(session_cookie, LOCAL_API_TOKEN):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: Missing or invalid session cookie."
            )
        # Check CSRF token header if provided, or verify same-origin browser metadata
        csrf_cookie = request.cookies.get("artemis_csrf_token")
        csrf_header = request.headers.get("X-CSRF-Token")
        if csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header):
            return "cookie"

        sec_fetch_site = request.headers.get("sec-fetch-site")
        origin = request.headers.get("origin")
        if sec_fetch_site in ["same-origin", "same-site"] and origin:
            parsed = urlparse(origin)
            if parsed.netloc.lower() in ALLOWED_HOSTS:
                return "cookie"

        raise HTTPException(
            status_code=403,
            detail="Forbidden: Missing or invalid CSRF token."
        )

    raise HTTPException(
        status_code=401,
        detail="Unauthorized: Missing or invalid API token."
    )

def verify_security(request: Request, _origin=Depends(verify_request_origin), _token=Depends(verify_api_token)):
    """Combined security dependency for sensitive device-control operations."""
    return True

# Initialize database
init_db()

# Controller singleton
controller = DeviceController()

# Mount frontend directory for static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_frontend_index(request: Request):
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # 1. Set HttpOnly=True, SameSite=Strict session cookie containing the authentication secret
        response.set_cookie(
            key="artemis_session_token",
            value=LOCAL_API_TOKEN,
            httponly=True,
            samesite="strict",
            path="/"
        )

        # 2. Set double-submit CSRF token (HttpOnly=False so frontend JS can read and send in X-CSRF-Token header)
        existing_csrf = request.cookies.get("artemis_csrf_token")
        csrf_value = existing_csrf if existing_csrf else secrets.token_hex(24)
        response.set_cookie(
            key="artemis_csrf_token",
            value=csrf_value,
            httponly=False,
            samesite="strict",
            path="/"
        )
        return response
    return JSONResponse(status_code=404, content={"message": "Frontend index.html not found"})

@app.get("/api/csrf-token")
def get_csrf_token(request: Request):
    """
    Returns the CSRF token and sets the cookies if not already set,
    ensuring browsers always have a valid token even if index.html was cached.
    """
    existing_csrf = request.cookies.get("artemis_csrf_token")
    csrf_value = existing_csrf if existing_csrf else secrets.token_hex(24)
    response = JSONResponse(content={"csrf_token": csrf_value})
    
    if not request.cookies.get("artemis_session_token"):
        response.set_cookie(
            key="artemis_session_token",
            value=LOCAL_API_TOKEN,
            httponly=True,
            samesite="strict",
            path="/"
        )
    if not existing_csrf:
        response.set_cookie(
            key="artemis_csrf_token",
            value=csrf_value,
            httponly=False,
            samesite="strict",
            path="/"
        )
    return response

@app.get("/api/health")
def health_check():
    gemini_status = controller.gemini.is_configured()
    adb_version = controller.adb.get_version()
    return {
        "status": "healthy",
        "gemini_configured": gemini_status,
        "adb_version": adb_version
    }

@app.get("/api/device/status", response_model=DeviceStatusResponse)
def get_device_status():
    status = controller.get_status()
    return DeviceStatusResponse(
        connected=status.get("connected", False),
        status=status.get("status", "Unknown"),
        model=status.get("model"),
        serial=status.get("serial"),
        connection_type=status.get("connection_type", "unknown"),
        current_app=status.get("current_app"),
        available_devices=status.get("available_devices", [])
    )

@app.post("/api/device/pair", response_model=WirelessResponse, dependencies=[Depends(verify_security)])
def pair_device(req: PairRequest):
    result = controller.pair_wireless(req.ip, req.port, req.code)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/pair-qr", response_model=WirelessResponse, dependencies=[Depends(verify_security)])
def pair_device_qr(req: QRPairRequest):
    result = controller.pair_with_qr(req.qr_payload, req.phone_ip)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message"),
        ip=result.get("ip"),
        port=result.get("port")
    )

@app.post("/api/device/connect", response_model=WirelessResponse, dependencies=[Depends(verify_security)])
def connect_device(req: ConnectRequest):
    result = controller.connect_wireless(req.ip, req.port)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/disconnect", response_model=WirelessResponse, dependencies=[Depends(verify_security)])
def disconnect_device(req: DisconnectRequest):
    result = controller.disconnect_wireless(req.target)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/select", response_model=WirelessResponse, dependencies=[Depends(verify_security)])
def select_device(req: SelectDeviceRequest):
    ok = controller.select_device(req.serial)
    return WirelessResponse(
        success=ok,
        message=f"Active target device set to: {req.serial}" if ok else "Failed to select device"
    )

@app.get("/api/device/screenshot")
def get_device_screenshot():
    latest_img = controller.get_latest_screenshot()
    if latest_img and os.path.exists(latest_img):
        return FileResponse(latest_img, media_type="image/png")
    
    # Return placeholder if no screenshot yet or failed
    placeholder = SCREENSHOTS_DIR / "placeholder.png"
    if not placeholder.exists():
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (360, 640), color=(30, 34, 42))
        d = ImageDraw.Draw(img)
        d.text((100, 300), "No screenshot captured\nConnect phone & refresh", fill=(160, 160, 160))
        img.save(str(placeholder))
    return FileResponse(str(placeholder), media_type="image/png")

@app.get("/api/task/progress")
def get_task_progress():
    progress = controller.get_progress()
    if progress:
        return progress
    return {"status": "idle", "task_id": None, "total_steps": 0, "current_step_index": 0}

@app.post("/api/execute", response_model=ExecuteResponse, dependencies=[Depends(verify_security)])
def execute_instruction(req: ExecuteRequest):
    result = controller.execute_instruction(req.instruction)
    return ExecuteResponse(**result)

@app.post("/api/stop", dependencies=[Depends(verify_security)])
def stop_automation():
    controller.stop_execution()
    return {"status": "success", "message": "Automation stop signal sent."}

@app.get("/api/history")
def get_history():
    return get_task_history(limit=50)

@app.post("/api/confirmation", dependencies=[Depends(verify_security)])
def handle_confirmation(req: ConfirmationRequest):
    res = controller.process_confirmation(req.task_id, req.approved)
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
