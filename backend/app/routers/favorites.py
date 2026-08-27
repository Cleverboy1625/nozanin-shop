from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


def _product_dict(product, db: Session) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "emoji": product.emoji,
        "description": product.description,
        "image_url": product.image_url,
        "variants": product.variants,
        "rating": round(db.query(func.avg(models.ProductRating.stars)).filter(
            models.ProductRating.product_id == product.id
        ).scalar() or 0, 1),
        "rating_count": db.query(models.ProductRating).filter(
            models.ProductRating.product_id == product.id
        ).count(),
    }


@router.get("", response_model=List[schemas.FavoriteOut])
def list_favorites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    favorites = (
        db.query(models.Favorite)
        .options(joinedload(models.Favorite.product).joinedload(models.Product.variants))
        .filter(models.Favorite.telegram_user_id == user["id"])
        .order_by(models.Favorite.created_at.desc())
        .all()
    )
    return [
        {
            "product": _product_dict(f.product, db),
            "created_at": f.created_at,
        }
        for f in favorites
    ]


@router.get("/ids", response_model=List[str])
def favorite_ids(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(models.Favorite.product_id)
        .filter(models.Favorite.telegram_user_id == user["id"])
        .all()
    )
    return [r[0] for r in rows]


@router.post("/{product_id}", status_code=201)
def add_favorite(product_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    existing = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.telegram_user_id == user["id"],
            models.Favorite.product_id == product_id,
        )
        .first()
    )
    if existing:
        return {"ok": True, "already": True}
    db.add(models.Favorite(telegram_user_id=user["id"], product_id=product_id))
    db.commit()
    return {"ok": True, "already": False}


@router.delete("/{product_id}")
def remove_favorite(product_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = (
        db.query(models.Favorite)
        .filter(
            models.Favorite.telegram_user_id == user["id"],
            models.Favorite.product_id == product_id,
        )
        .first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    return {"ok": True}
