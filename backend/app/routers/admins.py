from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/admins", tags=["admins"])


@router.get("/me", response_model=schemas.AdminCheckOut)
def check_me(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    admin = db.query(models.Admin).filter(models.Admin.telegram_user_id == user["id"]).first()
    if admin:
        return {"is_admin": True, "user_id": user["id"], "full_name": admin.full_name}
    return {"is_admin": False, "user_id": user["id"]}

@router.get("", response_model=list[schemas.AdminOut])
def list_admins(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.Admin).order_by(models.Admin.added_at.asc()).all()


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
    )
    db.add(seller)
    db.commit()
    db.refresh(seller)
    return seller
