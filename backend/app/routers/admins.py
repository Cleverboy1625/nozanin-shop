from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..config import is_configured_admin

router = APIRouter(prefix="/api/admins", tags=["admins"])


@router.get("/me", response_model=schemas.AdminCheckOut)
def check_me(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    admin = db.query(models.Admin).filter(models.Admin.telegram_user_id == user["id"]).first()
    if admin or is_configured_admin(user["id"]):
        role = "admin" if not admin or admin.role == "admin" else "seller"
        return {"is_admin": role == "admin", "is_seller": role == "seller", "role": role, "user_id": user["id"], "full_name": admin.full_name if admin else None}
    return {"is_admin": False, "is_seller": False, "role": None, "user_id": user["id"]}

@router.get("", response_model=list[schemas.AdminOut])
def list_admins(db: Session = Depends(get_db), admin=Depends(require_admin)):
    staff_list = db.query(models.Admin).order_by(models.Admin.added_at.asc()).all()
    return [
        {
            "id": staff.id,
            "telegram_user_id": staff.telegram_user_id,
            "full_name": staff.full_name,
            "role": staff.role,
            # .env dagi asosiy administrator tizimga kirishni saqlab qolishi kerak.
            "protected": is_configured_admin(staff.telegram_user_id),
        }
        for staff in staff_list
    ]


@router.post("", response_model=schemas.AdminOut, status_code=201)
def create_admin(payload: schemas.AdminIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    existing = db.query(models.Admin).filter(
        models.Admin.telegram_user_id == payload.telegram_user_id
    ).first()
    if existing:
        raise HTTPException(409, "Bu Telegram ID allaqachon sotuvchi")
    seller = models.Admin(
        telegram_user_id=payload.telegram_user_id,
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller


@router.delete("/{telegram_user_id}")
def delete_staff(telegram_user_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    staff = db.query(models.Admin).filter(models.Admin.telegram_user_id == telegram_user_id).first()
    if not staff:
        raise HTTPException(404, "Foydalanuvchi topilmadi")
    if is_configured_admin(telegram_user_id):
        raise HTTPException(400, "Konfiguratsiyadagi asosiy administratorni o'chirib bo'lmaydi")
    db.delete(staff)
    db.commit()
    return {"ok": True}
