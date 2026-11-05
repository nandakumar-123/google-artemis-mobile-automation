import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import FRONTEND_DIR, SCREENSHOTS_DIR, HOST, PORT
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

# Security: Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Controller singleton
controller = DeviceController()

# Mount frontend directory for static assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def serve_frontend_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        response = FileResponse(str(index_file))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return JSONResponse(status_code=404, content={"message": "Frontend index.html not found"})

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

@app.post("/api/device/pair", response_model=WirelessResponse)
def pair_device(req: PairRequest):
    result = controller.pair_wireless(req.ip, req.port, req.code)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/pair-qr", response_model=WirelessResponse)
def pair_device_qr(req: QRPairRequest):
    result = controller.pair_with_qr(req.qr_payload, req.phone_ip)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message"),
        ip=result.get("ip"),
        port=result.get("port")
    )

@app.post("/api/device/connect", response_model=WirelessResponse)
def connect_device(req: ConnectRequest):
    result = controller.connect_wireless(req.ip, req.port)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/disconnect", response_model=WirelessResponse)
def disconnect_device(req: DisconnectRequest):
    result = controller.disconnect_wireless(req.target)
    return WirelessResponse(
        success=result["success"],
        message=result["message"],
        output=result.get("message")
    )

@app.post("/api/device/select", response_model=WirelessResponse)
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

@app.post("/api/execute", response_model=ExecuteResponse)
def execute_instruction(req: ExecuteRequest):
    result = controller.execute_instruction(req.instruction)
    return ExecuteResponse(**result)

@app.post("/api/stop")
def stop_automation():
    controller.stop_execution()
    return {"status": "success", "message": "Automation stop signal sent."}

@app.get("/api/history")
def get_history():
    return get_task_history(limit=50)

@app.post("/api/confirmation")
def handle_confirmation(req: ConfirmationRequest):
    res = controller.process_confirmation(req.task_id, req.approved)
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
