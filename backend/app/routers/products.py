from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin, get_current_user
from ..report_service import send_product_post

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=List[schemas.ProductOut])
def list_products(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Product)
    if category and category != "hammasi":
        q = q.filter(models.Product.category == category)
    products = q.options(joinedload(models.Product.variants)).order_by(models.Product.created_at.desc()).all()
    return [
        {
            "id": product.id, "name": product.name, "category": product.category,
            "emoji": product.emoji, "description": product.description,
            "image_url": product.image_url, "variants": product.variants,
            "rating": round(db.query(func.avg(models.ProductRating.stars)).filter(
                models.ProductRating.product_id == product.id
            ).scalar() or 0, 1),
            "rating_count": db.query(models.ProductRating).filter(
                models.ProductRating.product_id == product.id
            ).count(),
        }
        for product in products
    ]


@router.post("/{product_id}/rating", response_model=schemas.RatingOut)
def rate_product(product_id: str, payload: schemas.RatingIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    rating = db.query(models.ProductRating).filter(
        models.ProductRating.product_id == product_id,
        models.ProductRating.telegram_user_id == user["id"],
    ).first()
    if rating:
        rating.stars = payload.stars
    else:
        db.add(models.ProductRating(product_id=product_id, telegram_user_id=user["id"], stars=payload.stars))
    db.commit()
    values = db.query(func.avg(models.ProductRating.stars), func.count(models.ProductRating.id)).filter(
        models.ProductRating.product_id == product_id
    ).one()
    return {"product_id": product_id, "rating": round(values[0] or 0, 1), "rating_count": values[1], "user_stars": payload.stars}


@router.post("", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if not payload.variants:
        raise HTTPException(400, "Kamida bitta variant kerak")
    product = models.Product(
        name=payload.name, category=payload.category, emoji=payload.emoji or "👗",
        description=payload.description or "", image_url=payload.image_url,
    )
    db.add(product)
    db.flush()
    for v in payload.variants:
        db.add(models.Variant(product_id=product.id, label=v.label, color=v.color,
                               price=v.price, stock_qty=v.stock_qty))
    db.commit()
    db.refresh(product)
    send_product_post(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: str, payload: schemas.ProductIn, db: Session = Depends(get_db), admin=Depends(require_admin)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    product.name = payload.name
    product.category = payload.category
    product.emoji = payload.emoji or "👗"
    product.description = payload.description or ""
    product.image_url = payload.image_url

    db.query(models.Variant).filter(models.Variant.product_id == product_id).delete()
    for v in payload.variants:
        db.add(models.Variant(product_id=product.id, label=v.label, color=v.color,
                               price=v.price, stock_qty=v.stock_qty))
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(product_id: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    db.delete(product)
    db.commit()
    return {"ok": True}
