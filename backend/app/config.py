import os
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))


def _env_csv(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return ",".join(part.strip() for part in str(value).split(",") if part.strip())


def _env_str(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default
    return str(value).strip()


def _webapp_url() -> str:
    value = _env_str("WEBAPP_URL", "https://nozanin-shoping.onrender.com").rstrip("/")
    if not value.startswith("https://") or "your-render" in value or "example.com" in value:
        return "https://nozanin-shoping.onrender.com"
    return value

DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(BACKEND_DIR, 'nozanin.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
if DATABASE_URL == "sqlite:///./nozanin.db":
    DATABASE_URL = DEFAULT_DATABASE_URL

class Settings:
    BOT_TOKEN: str = _env_str("BOT_TOKEN", "")
    USE_WEBHOOK: bool = _env_str("USE_WEBHOOK", "false").lower() in {"1", "true", "yes", "on"}
    DATABASE_URL: str = DATABASE_URL
    WEBAPP_URL: str = _webapp_url()
    ADMIN_TELEGRAM_IDS: str = _env_csv("ADMIN_TELEGRAM_IDS", "")  # vergul bilan ajratilgan
    PRODUCT_CHAT_IDS: str = _env_csv("PRODUCT_CHAT_IDS", "")  # kanal/gruppa ID yoki @username
    DAILY_REPORT_HOUR: int = int(_env_str("DAILY_REPORT_HOUR", "21"))
    DAILY_REPORT_MINUTE: int = int(_env_str("DAILY_REPORT_MINUTE", "0"))
    TIMEZONE: str = _env_str("TIMEZONE", "Asia/Tashkent")
    CORS_ORIGINS: str = _env_str("CORS_ORIGINS", "*")
    WEBHOOK_SECRET: str = _env_str("WEBHOOK_SECRET", "")
    BRAND_BANNER_URL: str = _env_str("BRAND_BANNER_URL", "")

settings = Settings()

def get_admin_ids_from_env():
    return [int(x.strip()) for x in settings.ADMIN_TELEGRAM_IDS.split(",") if x.strip() and x.strip().isdigit()]


def is_configured_admin(telegram_user_id: int) -> bool:
    return telegram_user_id in get_admin_ids_from_env()


def get_product_chat_ids():
    return [x.strip() for x in settings.PRODUCT_CHAT_IDS.split(",") if x.strip()]
