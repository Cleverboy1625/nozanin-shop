from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .telegram_verify import verify_init_data
from . import models
from .config import is_configured_admin


def get_current_user(x_telegram_init_data: str = Header(default="")):
    """Har bir so'rovda 'X-Telegram-Init-Data' header orqali Telegram foydalanuvchisini tekshiradi."""
    user = verify_init_data(x_telegram_init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Telegram autentifikatsiyasi muvaffaqiyatsiz (initData noto'g'ri)")
    return user


def require_admin(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.telegram_user_id == user["id"]).first()
    if admin and admin.role == "admin":
        return user
    if is_configured_admin(user["id"]):
        return user
    raise HTTPException(status_code=403, detail="Bu amal faqat administratorlar uchun")


def require_staff(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    staff = db.query(models.Admin).filter(models.Admin.telegram_user_id == user["id"]).first()
    if staff or is_configured_admin(user["id"]):
        return user
    raise HTTPException(status_code=403, detail="Bu amal uchun sotuvchi yoki administrator huquqi kerak")
