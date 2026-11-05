# Google Artemis Mobile Automation (Android AI Assistant)

An intelligent, multi-step Android phone automation assistant powered by **Google Gemini AI**, **Wireless / USB ADB (Android Debug Bridge)**, **FastAPI**, and a real-time web dashboard.

Control your Android smartphone (e.g. iQOO, Pixel, Samsung, etc.) seamlessly using natural language commands with verified step-by-step sequential execution, active screen inspection, dynamic UI element targeting, and robust error recovery.

---

## 🎥 Demo Video

https://github.com/user-attachments/assets/merged-1793878002901.mp4

> *Recorded live demonstration:* [`merged-1793878002901.mp4`](./merged-1793878002901.mp4)

<video src="merged-1793878002901.mp4" controls="controls" width="100%" height="auto"></video>

---

## ✨ Features

- **Gemini-Powered Multi-Step Task Planning:** Converts complex natural language instructions into ordered, sequential, and atomic actions.
- **Sequential Execution & Wait Management:** Executes actions one by one with dynamic `WAIT_FOR_APP` and `WAIT_FOR_ELEMENT` conditions.
- **Dynamic UI Detection (UIAutomator):** Locates UI elements dynamically using text, accessibility content descriptions, and resource IDs instead of fragile hard-coded coordinates.
- **Active Post-Action Screen Verification:** Confirms foreground package presence, UI hierarchy updates, and typed text before advancing to dependent steps.
- **Auto Error Recovery:** If an action misses or delays, the agent inspects the screen and retries safely up to configurable limits (`MAX_RETRIES_PER_STEP`).
- **Flexible Phone Connection Modes:**
  - **Wireless ADB via QR Code:** Scan phone pairing QR code with your laptop webcam.
  - **Wireless ADB via 6-Digit Pairing Code:** Pair using phone IP, pairing port, and code.
  - **USB Cable Debugging:** Zero-configuration instant connection over USB.
- **Real-Time Live Dashboard & Stop Control:** Track completed and running steps with instant task cancellation.
- **Safety Confirmations:** Blocks and prompts for user approval before sensitive operations (e.g. money transfer, file deletion, security settings).

---

## 🏗️ Architecture

```
phone_automation/
├── app/
│   ├── main.py               # FastAPI backend with REST endpoints
│   ├── config.py             # Environment configurations & safe limits
│   ├── gemini_service.py     # Google Gen AI client integration
│   ├── adb_manager.py        # Subprocess ADB controller & wireless pairing
│   ├── device_controller.py  # Automation pipeline & step execution engine
│   ├── screen_reader.py      # UI hierarchy dumper & screenshot capture
│   ├── action_planner.py     # Gemini & rule-based action planner
│   ├── action_executor.py    # Atomic action dispatcher with retry logic
│   ├── verification.py       # Post-action screen verification
│   ├── database.py           # SQLite local history storage
│   └── schemas.py            # Pydantic request/response schemas
├── frontend/
│   ├── index.html            # Dashboard with QR camera scanner & chat UI
│   ├── style.css             # Dark-themed responsive styles
│   ├── app.js                # Frontend controller & live progress polling
│   └── html5-qrcode.min.js   # QR code scanning library
├── tests/
│   ├── test_adb.py           # ADB integration & wireless pairing tests
│   ├── test_api.py           # FastAPI endpoint tests
│   └── test_planner.py       # Action planner unit tests
├── .env.example              # Template for environment settings
├── merged-1793878002901.mp4   # Demo video
├── requirements.txt          # Python dependencies
├── run.bat                   # 1-click startup script for Windows
├── stop.bat                  # Stop script
├── check_device.bat          # ADB device connection checker
├── LICENSE                   # MIT License
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **OS:** Windows 10/11
- **Python:** 3.10+ (Python 3.13 tested)
- **Android Phone:** Developer options enabled with USB or Wireless Debugging.

### 2. Installation
Clone the repository and set up a virtual environment:
```powershell
git clone https://github.com/nandakumar-123/google-artemis-mobile-automation.git
cd google-artemis-mobile-automation

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` and set your **Gemini API Key**:
```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
MAX_ACTION_STEPS=50
MAX_RETRIES_PER_STEP=2
ADB_TIMEOUT_SECONDS=20
HOST=127.0.0.1
PORT=8000
```
*(Get a free key from [Google AI Studio](https://aistudio.google.com/)).*

### 4. Run the Application
Double-click `run.bat` or run:
```powershell
.\run.bat
```
The browser will automatically open at: **http://127.0.0.1:8000**

---

## 📱 Connecting Your Android Phone

### Option A: USB Cable (Fastest)
1. Connect your phone via USB cable.
2. In **Settings** → **Developer Options**, enable **USB Debugging**.
3. Accept the *"Always allow from this computer"* prompt on your phone screen.
4. Click **Refresh** in the web dashboard.

### Option B: Wireless Debugging (Pairing Code)
1. Ensure your PC and phone are connected to the same Wi-Fi / Hotspot.
2. Go to **Settings** → **Developer Options** → **Wireless Debugging** → tap **Pair device with pairing code**.
3. In the web dashboard:
   - Click the **Pairing Code** tab.
   - Enter your Phone IP, Pairing Port, and 6-Digit Code.
   - Click **Pair with Code**.
4. Switch to the **Connect** tab, enter the Connection Port, and click **Connect ADB**.

---

## 💬 Example Commands to Try

- `"Open YouTube, search for AI Engineer roadmap, open the first relevant video and play it."`
- `"Open Settings and find Battery."`
- `"Open Chrome and search for machine learning."`
- `"Open Play Store and search for Spotify."`
- `"Capture my phone screen and explain."`
- `"Go back to previous screen."`

---

## 🧪 Running Tests

Run the full pytest suite:
```powershell
.\.venv\Scripts\python.exe -m pytest
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
