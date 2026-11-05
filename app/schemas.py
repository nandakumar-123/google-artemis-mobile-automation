from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class ActionItem(BaseModel):
    type: str = Field(..., description="Action type like OPEN_APP, TAP_TEXT, TAP_CONTENT_DESCRIPTION, TAP_COORDINATES, TYPE_TEXT, PRESS_ENTER, KEYEVENT, SWIPE, PRESS_BACK, PRESS_HOME, WAIT, WAIT_FOR_ELEMENT, WAIT_FOR_APP, TAKE_SCREENSHOT, READ_SCREEN, ASK_CONFIRMATION")
    app_name: Optional[str] = None
    package_name: Optional[str] = None
    text: Optional[str] = None
    content_description: Optional[str] = None
    resource_id: Optional[str] = None
    class_name: Optional[str] = None
    match_index: Optional[int] = 0
    fallback_text: Optional[str] = None
    fallback_content_description: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    direction: Optional[str] = None  # up, down, left, right
    seconds: Optional[float] = 1.0
    timeout: Optional[float] = 10.0
    keycode: Optional[int] = None
    reason: Optional[str] = None
    verify: Optional[bool] = True
    retry_count: Optional[int] = 2

class ActionPlan(BaseModel):
    task: str
    actions: List[ActionItem] = []
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    validation_status: Optional[str] = "valid"  # "valid", "clamped", "invalid"
    notes: Optional[str] = None

class TaskProgress(BaseModel):
    task_id: int
    instruction: str
    status: str  # "idle", "planning", "running", "completed", "failed", "cancelled", "awaiting_confirmation"
    total_steps: int = 0
    current_step_index: int = 0
    current_action: Optional[str] = None
    completed_steps: List[Dict[str, Any]] = []
    failed_steps: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    screenshot_url: Optional[str] = None

class ExecuteRequest(BaseModel):
    instruction: str

class ExecuteResponse(BaseModel):
    task_id: int
    instruction: str
    success: bool
    message: str
    actions_executed: List[Dict[str, Any]] = []
    screenshot_url: Optional[str] = None
    requires_confirmation: bool = False
    pending_action: Optional[ActionItem] = None

class ConfirmationRequest(BaseModel):
    task_id: int
    approved: bool

class DeviceStatusResponse(BaseModel):
    connected: bool
    status: str
    model: Optional[str] = None
    serial: Optional[str] = None
    connection_type: Optional[str] = "unknown" # "usb", "wireless", "unknown"
    current_app: Optional[str] = None
    error: Optional[str] = None
    available_devices: List[Dict[str, str]] = []

class PairRequest(BaseModel):
    ip: str = Field(..., description="Phone IP Address")
    port: int = Field(..., description="Pairing port shown under 'Pair device with pairing code'")
    code: str = Field(..., description="6-digit Wi-Fi pairing code")

class ConnectRequest(BaseModel):
    ip: str = Field(..., description="Phone IP Address")
    port: int = Field(..., description="Connection port shown under Wireless debugging")

class DisconnectRequest(BaseModel):
    target: Optional[str] = Field(None, description="Optional IP:PORT to disconnect, or disconnect all")

class SelectDeviceRequest(BaseModel):
    serial: str = Field(..., description="Device serial or IP:PORT to select for automation")

class QRPairRequest(BaseModel):
    qr_payload: str = Field(..., description="Raw string scanned from QR code or decoded JSON")
    phone_ip: Optional[str] = Field(None, description="Optional fallback phone IP address if not in QR payload")

class WirelessResponse(BaseModel):
    success: bool
    message: str
    output: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
