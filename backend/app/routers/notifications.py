from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=List[schemas.NotificationOut])
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Notification).filter(models.Notification.telegram_user_id == user["id"]).order_by(models.Notification.created_at.desc()).all()


@router.post("", response_model=schemas.NotificationOut, status_code=201)
def create_notification(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    user_id = payload.get("telegram_user_id")
    if not user_id:
        raise HTTPException(400, "telegram_user_id kerak")
    notification = models.Notification(
        telegram_user_id=int(user_id),
        title=str(payload.get("title", "Notification")),
        body=str(payload.get("body", "")),
        kind=str(payload.get("kind", "info")),
        is_read=0,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    note = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.telegram_user_id == user["id"]).first()
    if not note:
        raise HTTPException(404, "Bildirishnoma topilmadi")
    note.is_read = 1
    db.commit()
    return {"ok": True}
