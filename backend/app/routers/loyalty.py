from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/loyalty", tags=["loyalty"])


@router.get("", response_model=List[schemas.LoyaltyOfferOut])
def list_loyalty_offers(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.LoyaltyOffer).filter(models.LoyaltyOffer.active == 1).order_by(models.LoyaltyOffer.created_at.desc()).all()


@router.post("", response_model=schemas.LoyaltyOfferOut, status_code=201)
def create_offer(payload: schemas.LoyaltyOfferIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    offer = models.LoyaltyOffer(
        title=payload.title,
        description=payload.description,
        offer_type=payload.offer_type,
        value=payload.value,
        min_total=payload.min_total,
        active=1 if payload.active else 0,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.patch("/{offer_id}")
def update_offer(offer_id: str, payload: schemas.LoyaltyOfferIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    offer = db.query(models.LoyaltyOffer).filter(models.LoyaltyOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Taklif topilmadi")
    for field, value in payload.model_dump().items():
        setattr(offer, field, value)
    offer.active = 1 if payload.active else 0
    db.commit()
    return {"ok": True}


@router.delete("/{offer_id}")
def delete_offer(offer_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    offer = db.query(models.LoyaltyOffer).filter(models.LoyaltyOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Taklif topilmadi")
    db.delete(offer)
    db.commit()
    return {"ok": True}
