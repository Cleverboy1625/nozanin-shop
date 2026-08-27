from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/promos", tags=["promos"])


def calculate_discount(promo: models.PromoCode, order_total: int) -> int:
    if promo.discount_type == "percent":
        return round(order_total * promo.discount_value / 100)
    return min(promo.discount_value, order_total)


@router.post("/validate", response_model=schemas.PromoValidOut)
def validate_promo(payload: schemas.PromoValidIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    promo = db.query(models.PromoCode).filter(models.PromoCode.code == payload.code.strip()).first()
    if not promo:
        return {"valid": False, "code": payload.code, "message": "Kod topilmadi"}
    if not promo.active:
        return {"valid": False, "code": payload.code, "message": "Bu kod faol emas"}
    if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
        return {"valid": False, "code": payload.code, "message": "Bu kod limit tugagan"}
    if promo.expires_at and promo.expires_at < datetime.utcnow():
        return {"valid": False, "code": payload.code, "message": "Bu kod muddati tugagan"}
    if payload.order_total < promo.min_order_total:
        return {
            "valid": False, "code": payload.code,
            "message": f"Minimal buyurtma summasi {promo.min_order_total:,} so'm",
            "min_order_total": promo.min_order_total,
        }

    discount = calculate_discount(promo, payload.order_total)
    return {
        "valid": True,
        "code": promo.code,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "min_order_total": promo.min_order_total,
        "discount_amount": discount,
        "message": f"Chegirma qo'llanildi: {discount:,} so'm",
    }


@router.get("", response_model=list[schemas.PromoValidOut])
def list_promos(db: Session = Depends(get_db), admin=Depends(require_admin)):
    promos = db.query(models.PromoCode).order_by(models.PromoCode.created_at.desc()).all()
    return [
        {
            "valid": bool(p.active),
            "code": p.code,
            "discount_type": p.discount_type,
            "discount_value": p.discount_value,
            "min_order_total": p.min_order_total,
            "discount_amount": 0,
            "message": f"used {p.used_count}/{p.usage_limit}" if p.usage_limit else f"used {p.used_count}",
        }
        for p in promos
    ]


@router.post("", status_code=201)
def create_promo(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    code = str(payload.get("code", "")).strip()
    if not code:
        raise HTTPException(400, "Kod kiritilishi shart")
    existing = db.query(models.PromoCode).filter(models.PromoCode.code == code).first()
    if existing:
        raise HTTPException(409, "Bu kod allaqachon mavjud")
    promo = models.PromoCode(
        code=code,
        discount_type=payload.get("discount_type", "percent"),
        discount_value=int(payload.get("discount_value", 0)),
        min_order_total=int(payload.get("min_order_total", 0)),
        usage_limit=int(payload["usage_limit"]) if payload.get("usage_limit") else None,
        active=1 if payload.get("active", True) else 0,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {
        "valid": bool(promo.active),
        "code": promo.code,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "min_order_total": promo.min_order_total,
        "discount_amount": 0,
        "message": "Kod yaratildi",
    }


@router.delete("/{code}")
def delete_promo(code: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    promo = db.query(models.PromoCode).filter(models.PromoCode.code == code).first()
    if not promo:
        raise HTTPException(404, "Kod topilmadi")
    db.delete(promo)
    db.commit()
    return {"ok": True}
