import os
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(BACKEND_DIR, 'nozanin.db')}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
if DATABASE_URL == "sqlite:///./nozanin.db":
    DATABASE_URL = DEFAULT_DATABASE_URL

class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = DATABASE_URL
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://example.com")
    ADMIN_TELEGRAM_IDS: str = os.getenv("ADMIN_TELEGRAM_IDS", "")  # vergul bilan ajratilgan
    PRODUCT_CHAT_IDS: str = os.getenv("PRODUCT_CHAT_IDS", "")  # kanal/gruppa ID yoki @username
    DAILY_REPORT_HOUR: int = int(os.getenv("DAILY_REPORT_HOUR", "21"))
    DAILY_REPORT_MINUTE: int = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

settings = Settings()

def get_admin_ids_from_env():
    return [int(x.strip()) for x in settings.ADMIN_TELEGRAM_IDS.split(",") if x.strip().isdigit()]


def get_product_chat_ids():
    return [x.strip() for x in settings.PRODUCT_CHAT_IDS.split(",") if x.strip()]
