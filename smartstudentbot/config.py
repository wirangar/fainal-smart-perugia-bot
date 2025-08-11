import os
from datetime import time

def _as_bool(val: str | None, default=False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}

# --- Development and Safety Flags ---
# When True, disables external network calls, etc., for safe local running.
DEV_MODE = _as_bool(os.getenv("DEV_MODE"), True)
# A more granular flag to disable network calls even if not in DEV_MODE.
DISABLE_EXTERNAL_CALLS = _as_bool(os.getenv("DISABLE_EXTERNAL_CALLS"), True)
# Flags to control specific startup actions. Default to False for development.
STARTUP_SET_WEBHOOK = _as_bool(os.getenv("STARTUP_SET_WEBHOOK"), False)
STARTUP_CONNECT_DB = _as_bool(os.getenv("STARTUP_CONNECT_DB"), False)
STARTUP_CONNECT_REDIS = _as_bool(os.getenv("STARTUP_CONNECT_REDIS"), False)


# --- Bot Configuration ---
BOT_ID = os.getenv("BOT_ID", "perugia")
CITY_NAME = os.getenv("CITY_NAME", "Perugia")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_IDS = os.getenv("ADMIN_CHAT_IDS", "7801271819").split(",")
ADMIN_ROLES = {id: "OWNER" if id == "7801271819" else "ADMIN" for id in ADMIN_CHAT_IDS}
CHANNEL_ID = os.getenv("CHANNEL_ID", "@YourChannel")
BASE_URL = os.getenv("BASE_URL", "https://new-bot-szsf.onrender.com")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "SeYeDEhSaNaBaVi1367")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
SQLITE_DB = os.getenv("SQLITE_DB", "data.db")
GOOGLE_CREDS = os.getenv("GOOGLE_CREDS")
GOOGLE_DRIVE_CREDS = os.getenv("GOOGLE_DRIVE_CREDS")
GOOGLE_DRIVE_UPLOAD_FOLDER_ID = os.getenv("GOOGLE_DRIVE_UPLOAD_FOLDER_ID")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SHEET_ID = os.getenv("SHEET_ID")
QUESTIONS_SHEET_NAME = os.getenv("QUESTIONS_SHEET_NAME", "StudentBotQuestions")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Scholarship")
JSON_VERSION = "1.0"
ISEE_THRESHOLD = 23000
FEATURE_FLAGS = {
    "GAMIFICATION": _as_bool(os.getenv("FEATURE_GAMIFICATION", "1")),
    "PODCASTS": _as_bool(os.getenv("FEATURE_PODCASTS", "1")),
    "ROOMMATE": _as_bool(os.getenv("FEATURE_ROOMMATE", "1")),
    "NEWS": _as_bool(os.getenv("FEATURE_NEWS", "1")),
    "AI": _as_bool(os.getenv("FEATURE_AI", "0")),  # Disabled in dev by default
}

# --- Web Admin Panel ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "supersecretpassword") # CHANGE THIS IN PRODUCTION
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "another-super-secret-key") # For signing cookies
