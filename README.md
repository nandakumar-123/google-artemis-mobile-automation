# Google ARTEMIS Mobile Automation (Android AI Assistant)

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Google Gemini API](https://img.shields.io/badge/Google%20Gen%20AI-Gemini%20API-4285F4.svg?logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: Pytest](https://img.shields.io/badge/Tests-22%20Passed-brightgreen.svg)](tests/)

An intelligent Android mobile phone automation assistant powered by **Google Gemini AI**, **Android Debug Bridge (ADB)**, **FastAPI**, and a real-time web dashboard.

Translate complex natural-language instructions into ordered, verified mobile device actions executed sequentially on a physical Android phone or emulator over **Wireless ADB (QR code or 6-digit pairing code)** or **USB Cable Debugging**.

> **Disclaimer:** This is an independently developed open-source integration project created to demonstrate AI-driven mobile automation using Google's Gemini API and Android ADB. This repository is **not** an official Google product and is neither affiliated with nor endorsed by Google LLC.

---

## 🎥 Demonstration Video

Direct video file in repository: [`merged-1793878002901.mp4`](./merged-1793878002901.mp4)

https://github.com/user-attachments/assets/merged-1793878002901.mp4

<video src="merged-1793878002901.mp4" controls="controls" width="100%" height="auto"></video>

---

## ✨ Key Capabilities

1. **Natural-Language Action Planning:** Converts high-level instructions (e.g. *"Open YouTube, search for AI Engineer roadmap, open the first relevant video and play it"*) into structured, atomic steps.
2. **Sequential Multi-Step Execution:** Executes one action at a time; never triggers dependent operations simultaneously or blindly.
3. **Active Post-Action Screen Verification:** Inspects foreground activity (`dumpsys`) and UI hierarchy (`dumpsys window`) after actions to verify state transitions before proceeding.
4. **Dynamic UI Element Detection:** Utilizes Android UIAutomator XML hierarchy inspection (matching text, `content-desc`, resource IDs, and result indexes) instead of fragile fixed pixel coordinates.
5. **Wait & App Lifecycle Management:** Automatically inserts dynamic waits (`WAIT_FOR_APP`, `WAIT_FOR_ELEMENT`) to ensure pages and network responses load before issuing tap/type events.
6. **Error Recovery & Retries:** Detects missing elements or UI delays, pauses, inspects screen state, and safely retries failed steps up to configurable limits.
7. **Immediate Task Cancellation:** Stop running multi-step sequences instantly from the web interface.
8. **Live Visual Dashboard:** Shows step-by-step progress badges (`SUCCESS`, `FAILED`, `STOPPED`), action parameters, verification details, and live phone screen captures.
9. **Safety Confirmation Guard:** Intercepts sensitive instructions (e.g. money transfers, deletions, permissions, or system resets) with interactive modal confirmation.
10. **Flexible Connection Modes:**
    - **Wireless ADB via QR Code:** Scan phone pairing QR code with your laptop webcam.
    - **Wireless ADB via 6-Digit Pairing Code:** Connect over Wi-Fi/Hotspot using Android's pairing port and code.
    - **USB Debugging:** Plug-and-play instant connection with auto-detection.

---

## 🏗️ Architecture & Technology Stack

```
                                  +---------------------------------------+
                                  |         Web Frontend Dashboard        |
                                  |  (HTML5 / CSS / Vanilla JS / Canvas)  |
                                  +-------------------+-------------------+
                                                      |  REST / Event Polling
                                                      v
                                  +-------------------+-------------------+
                                  |         FastAPI Backend Server        |
                                  +-------------------+-------------------+
                                                      |
                         +----------------------------+----------------------------+
                         |                                                         |
                         v                                                         v
         +---------------+---------------+                         +---------------+---------------+
         |     Gemini Planning Engine    |                         |       Device Controller       |
         | (Official google-genai SDK /  |                         |  - Action Planner & Validator |
         |   Rule-Based Safe Fallback)   |                         |  - Sequential Step Executor   |
         +-------------------------------+                         |  - Action Verifier & Retries  |
                                                                   +---------------+---------------+
                                                                                   |
                                                                                   v
                                                                   +---------------+---------------+
                                                                   |       ADB Manager Core        |
                                                                   |   (Subprocess / mDNS / AOSP)  |
                                                                   +---------------+---------------+
                                                                                   |
                                                                 +-----------------+-----------------+
                                                                 |                                   |
                                                                 v (TCP/IP Wi-Fi)                    v (USB Cable)
                                                   +-------------------------------+   +-------------------------------+
                                                   |    Wireless Android Phone     |   |      USB Connected Phone      |
                                                   +-------------------------------+   +-------------------------------+
```

### Technology Stack
- **AI & Language Models:** Google Gemini API (`gemini-3.5-flash-lite`, `google-genai` SDK).
- **Backend Framework:** Python 3.10+, FastAPI, Uvicorn (ASGI).
- **Mobile Device Control:** Android Debug Bridge (ADB), Android UIAutomator XML dump engine.
- **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3, `html5-qrcode.min.js`.
- **Database & Storage:** SQLite3 (local persistent task history).
- **Image & Data Processing:** Pillow, DefusedXML, Pydantic v2.

---

## 📁 Repository Structure

```
google-artemis-mobile-automation/
├── app/
│   ├── main.py               # FastAPI application, REST endpoints, and router
│   ├── config.py             # Environment configurations, paths, and timeouts
│   ├── gemini_service.py     # Gemini client integration & fallback management
│   ├── adb_manager.py        # ADB subprocess wrapper, QR parser, and mDNS discovery
│   ├── device_controller.py  # Central orchestration pipeline, retries, and cancellation
│   ├── screen_reader.py      # UIAutomator parser and dynamic element finder
│   ├── action_planner.py     # Structured task planning and plan validation
│   ├── action_executor.py    # Atomic action dispatcher (tap, type, wait, swipe, keys)
│   ├── verification.py       # Post-action screen verification and state checking
│   ├── database.py           # SQLite persistence for task history and results
│   └── schemas.py            # Pydantic models for action items, plans, and API contracts
├── frontend/
│   ├── index.html            # Dashboard UI with QR webcam scanner and chat interface
│   ├── style.css             # Dark-themed responsive dashboard styles
│   ├── app.js                # Frontend controller, event handling, and progress polling
│   └── html5-qrcode.min.js   # Local QR-code scanning library (Apache 2.0)
├── tests/
│   ├── test_adb.py           # Unit tests for ADBManager, QR parsing, and device commands
│   ├── test_api.py           # API endpoint integration tests using FastAPI TestClient
│   └── test_planner.py       # Planner tests for YouTube, navigation, and sensitive actions
├── .env.example              # Template for environment configuration
├── .gitignore                # Git exclusion rules (protects .env, binaries, and caches)
├── check_device.bat          # Windows utility script to check ADB connection
├── LICENSE                   # MIT License
├── merged-1793878002901.mp4   # Demonstration video file
├── README.md                 # Project documentation
├── requirements.txt          # Python dependency list
├── run.bat                   # 1-click startup script for Windows
├── setup.bat                 # Automated virtual environment and dependency setup script
├── stop.bat                  # Clean shutdown script for background server process
└── THIRD_PARTY_NOTICES.md    # Upstream open-source notices and licenses
```

---

## ⚙️ Prerequisites

1. **Operating System:** Windows 10/11, macOS, or Linux.
2. **Python:** Version 3.10, 3.11, 3.12, or 3.13.
3. **Android Device:** Physical Android smartphone (Android 11+ recommended for Wireless Debugging) or Android Emulator.
4. **Android SDK Platform-Tools:** `adb` installed and accessible in your system `PATH` (or placed in the project folder under `platform-tools/`).
5. **Google Gemini API Key:** (Optional for rule-based mode, required for AI reasoning). Obtainable for free at [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/nandakumar-123/google-artemis-mobile-automation.git
cd google-artemis-mobile-automation
```

### 2. Set Up Python Environment
#### On Windows (Automated):
```cmd
.\setup.bat
```
#### On Windows / macOS / Linux (Manual):
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to create your private `.env` file:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` with your settings:
```ini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
ADB_PATH=
MAX_ACTION_STEPS=50
MAX_RETRIES_PER_STEP=2
ADB_TIMEOUT_SECONDS=20
HOST=127.0.0.1
PORT=8000
LOCAL_API_TOKEN=YOUR_LOCAL_API_TOKEN
```
*(Leave `ADB_PATH=` blank if `adb` is in your system PATH or located in `platform-tools/adb.exe`. If `LOCAL_API_TOKEN` is left empty, the server automatically generates a secure cryptographic token at startup).*

---

## 📱 Connecting Your Android Phone

### Method A: USB Cable Debugging (Fastest & Most Stable)
1. Connect your Android phone to your computer with a USB cable.
2. On your phone: Go to **Settings** → **About Phone** → tap **Build Number** 7 times to enable Developer Options.
3. Open **Settings** → **Developer Options** → enable **USB Debugging**.
4. Unlock your phone screen and tap **Always allow from this computer** on the RSA authorization prompt.
5. In the web dashboard, click **Refresh** under Active Device. The badge will turn green (**Connected**).

### Method B: Wireless ADB via Pairing Code
1. Connect your PC and phone to the **same Wi-Fi network or mobile hotspot**.
2. On your phone: Open **Settings** → **Developer Options** → enable **Wireless Debugging**.
3. Tap **Pair device with pairing code**. Note the temporary **IP:Port** (e.g. `192.168.1.45:39123`) and the **6-digit pairing code**.
4. In the web dashboard:
   - Click the **Pairing Code** tab.
   - Enter your phone's IP, Pairing Port, and 6-digit code.
   - Click **Pair with Code**.
5. Switch to the **Connect** tab in the dashboard:
   - Look at the main Wireless Debugging screen on your phone for the **Connection Port** (e.g. `41235`).
   - Enter the IP and Connection Port, then click **Connect ADB**.

### Method C: Wireless ADB via QR Code
1. On your phone: Open **Settings** → **Developer Options** → **Wireless Debugging** → tap **Pair device with QR code**.
2. In the web dashboard: Open the **QR Code Pair** tab and click **Start Camera**.
3. Point your phone's screen toward your webcam to scan the pairing token.

---

## 🏃 Running the Application

### Option 1: One-Click Launch (Windows)
Double-click `run.bat` or run:
```cmd
.\run.bat
```
This automatically verifies dependencies, starts the FastAPI server at `http://127.0.0.1:8000`, and opens your default browser.

### Option 2: Direct Command Line
```bash
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💬 Example Natural-Language Commands

Type any of the following instructions into the dashboard chat bar:

- `"Open YouTube, search for AI Engineer roadmap, open the first relevant video and play it."`
- `"Open Settings and check Battery status."`
- `"Open Google Chrome and search for machine learning tutorials."`
- `"Open Play Store and find Spotify."`
- `"Scroll down and tap Display."`
- `"Take a screenshot and inspect the screen."`
- `"Go back to the previous screen."`

---

## 🔌 API Endpoints Reference

The FastAPI backend exposes standard REST endpoints documented interactively at `http://127.0.0.1:8000/docs`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web dashboard UI |
| `GET` | `/api/health` | Health status and ADB/Gemini configuration state |
| `GET` | `/api/device/status` | Current device connectivity, active model, serial, and foreground app |
| `POST` | `/api/device/pair` | Pair phone via IP, pairing port, and 6-digit code |
| `POST` | `/api/device/pair-qr` | Pair phone via scanned QR code token payload |
| `POST` | `/api/device/connect` | Connect to paired Wireless ADB target |
| `POST` | `/api/device/disconnect` | Disconnect active wireless target |
| `POST` | `/api/device/select` | Select active device when multiple phones are connected |
| `GET` | `/api/device/screenshot`| Fetch latest high-resolution device screenshot |
| `POST` | `/api/execute` | Dispatch natural-language automation instruction |
| `GET` | `/api/task/progress` | Poll real-time multi-step task progress |
| `POST` | `/api/stop` | Send immediate cancellation signal to abort running task |
| `POST` | `/api/confirmation` | Approve or reject sensitive action prompt |
| `GET` | `/api/history` | Retrieve persistent history of past tasks |

---

## 🧪 Testing

The repository contains automated unit and integration tests using `pytest`:

```bash
# Run all tests
.\.venv\Scripts\python.exe -m pytest

# Run specific test suites
.\.venv\Scripts\python.exe -m pytest tests/test_adb.py
.\.venv\Scripts\python.exe -m pytest tests/test_api.py
.\.venv\Scripts\python.exe -m pytest tests/test_planner.py
```

### Verified Test Results (30/30 Passed):
- `tests/test_adb.py`: **9 passed** (initialization, version parsing, connection check, already-paired avoidance, QR payload formats).
- `tests/test_api.py`: **18 passed** (health endpoint, device status, history, stop signal, disconnect, device select, QR error checks, local API token validation, unauthorized missing/invalid token rejection, missing origin rejection, cross-site origin blocking, Bearer token authorization, HttpOnly and SameSite=Strict cookie flags, removal of raw token endpoint, valid CSRF cookie auth, and CSRF attack/mismatch rejection).
- `tests/test_planner.py`: **3 passed** (YouTube multi-step planning, navigation commands, sensitive action confirmation guards).

---

## 🛡️ Security Considerations

- **Secrets Management:** The repository `.gitignore` ensures that `.env`, session databases, and logs are never committed. Placeholders are maintained in `.env.example`.
- **HttpOnly Cookie Authentication with CSRF Protection:** Dashboard requests authenticate via an `HttpOnly=True` and `SameSite=Strict` session cookie (`artemis_session_token`). In addition, cross-site request forgery protection is enforced using a double-submit CSRF cookie token (`artemis_csrf_token`) validated against the `X-CSRF-Token` header.
- **Header Authentication for API Clients:** External API clients authenticate using standard HTTP headers (`X-API-Token: <token>` or `Authorization: Bearer <token>`).
- **No Client-Exposed Raw Secret:** The `/api/auth/token` endpoint has been removed to prevent raw API keys or tokens from being exposed to frontend JavaScript.
- **Persistent Token Generation:** When `LOCAL_API_TOKEN` is not explicitly defined in `.env`, a cryptographically random token is generated and persisted in `data/.local_token` to maintain session validity across server restarts.
- **Strict Request-Origin Validation:** All state-changing device-control endpoints strictly require either `Origin` or `Referer` headers matching local authorized hosts (`127.0.0.1`, `localhost`). Requests lacking origin metadata or exhibiting cross-site properties (`sec-fetch-site: cross-site`) are blocked with HTTP 403 Forbidden.
- **Strict Local Access Controls:** In addition to origin checks, CORS is restricted to local addresses (`127.0.0.1` and `localhost`).
- **Command Sanitization:** Text entered through `TYPE_TEXT` is escaped to avoid shell injection in ADB commands.
- **Sensitive Operations Guard:** The planner automatically detects sensitive keywords (e.g. *pay*, *delete*, *uninstall*, *format*, *factory reset*, *send message*) and prompts for interactive user confirmation before execution.
- **Safe Network Limits:** The server binds locally to `127.0.0.1` by default to prevent unauthorized network exposure.

---

## ❓ Troubleshooting

| Issue | Likely Cause | Solution |
|---|---|---|
| `Device: Disconnected` | USB debugging is not enabled or unauthorized | Disconnect and reconnect USB cable; tap "Always allow from this computer" on phone prompt. |
| `Pairing failed` | Phone IP or Pairing Port changed | Android generates a new random pairing port each time "Pair device with pairing code" is opened. Use the active port shown on your phone screen. |
| `Task stopped halfway` | Network latency or slow app loading | The engine automatically pauses and retries. Ensure your phone is awake and not locked with a PIN. |
| `Port 8000 already in use` | A previous server instance is still running | Run `.\stop.bat` to terminate orphaned server processes, then run `.\run.bat`. |

---

## 📜 License & Third-Party Notices

- This project is open-source software licensed under the **[MIT License](LICENSE)**.
- Third-party components, including Google Gen AI Python SDK, Android Platform Tools (ADB), FastAPI, and html5-qrcode, are used under their respective open-source licenses. See **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)** for details.

---

## 👤 Author & Acknowledgments

- **Author:** Nandakumar Anandrajan ([nandakumar-123](https://github.com/nandakumar-123))
- **Contact:** [nandakumaranandrajan@gmail.com](mailto:nandakumaranandrajan@gmail.com)
- **GitHub:** [Nandakumar-123](https://github.com/nandakumar-123)
- **Repository:** [Google Artemis Mobile Automation](https://github.com/nandakumar-123/google-artemis-mobile-automation)

### Acknowledgments
- **Google:** For Gemini AI and the related developer technologies used in this project.
- **Open-source contributors:** For the libraries and tools that support this project.
- *This is an independent project and is not officially affiliated with or endorsed by Google.*
