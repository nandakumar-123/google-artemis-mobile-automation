import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Detect platform-tools relative to BASE_DIR if ADB_PATH is not set or not found
default_adb = BASE_DIR / "platform-tools" / "adb.exe"
ADB_PATH = os.getenv("ADB_PATH", "")
if not ADB_PATH or not Path(ADB_PATH).exists():
    if default_adb.exists():
        ADB_PATH = str(default_adb)
    else:
        ADB_PATH = "adb"

MAX_ACTION_STEPS = int(os.getenv("MAX_ACTION_STEPS", "50"))
MAX_RETRIES_PER_STEP = int(os.getenv("MAX_RETRIES_PER_STEP", "2"))
ADB_TIMEOUT_SECONDS = int(os.getenv("ADB_TIMEOUT_SECONDS", "25"))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Paths
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
HISTORY_DIR = DATA_DIR / "history"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = DATA_DIR / "automation.db"
FRONTEND_DIR = BASE_DIR / "frontend"

for directory in [DATA_DIR, SCREENSHOTS_DIR, HISTORY_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Local API authentication token
_configured_token = os.getenv("LOCAL_API_TOKEN", "").strip()
_token_file = DATA_DIR / ".local_token"

if _configured_token:
    LOCAL_API_TOKEN = _configured_token
else:
    # Persist auto-generated token in DATA_DIR across server restarts
    if _token_file.exists():
        try:
            LOCAL_API_TOKEN = _token_file.read_text(encoding="utf-8").strip()
        except Exception:
            LOCAL_API_TOKEN = ""
    else:
        LOCAL_API_TOKEN = ""

    if not LOCAL_API_TOKEN:
        LOCAL_API_TOKEN = secrets.token_hex(32)
        try:
            _token_file.write_text(LOCAL_API_TOKEN, encoding="utf-8")
        except Exception:
            pass


