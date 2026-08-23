"""
Telegram Mini App initData ni tekshirish (HMAC-SHA256).
Rasmiy hujjat: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from typing import Optional, Dict
from .config import settings

INIT_DATA_MAX_AGE_SECONDS = 86400


def verify_init_data(init_data: str) -> Optional[Dict]:
    """initData satrini tekshiradi. To'g'ri bo'lsa foydalanuvchi ma'lumotini qaytaradi, aks holda None."""
    if not init_data or not settings.BOT_TOKEN:
        return None
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    try:
        auth_date = int(parsed.get("auth_date", "0"))
    except ValueError:
        return None
    if auth_date <= 0 or time.time() - auth_date > INIT_DATA_MAX_AGE_SECONDS:
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError:
        return None
    return user


def dev_fallback_user(init_data: str) -> Optional[Dict]:
    """
    Faqat local test uchun: agar BOT_TOKEN bo'sh bo'lsa yoki DEV rejimda ishlatilsa,
    initData tekshirmasdan sinov foydalanuvchisi qaytaradi. PRODUCTIONDA HECH QACHON ishlatilmasin.
    """
    return {"id": 1, "first_name": "Test", "username": "test_user"}
