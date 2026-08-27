from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.get("", response_model=List[schemas.CartItemOut])
def list_cart(db: Session = Depends(get_db), user=Depends(get_current_user)):
    items = db.query(models.CartItem).filter(models.CartItem.telegram_user_id == user["id"]).all()
    out = []
    for item in items:
        product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
        variant = db.query(models.Variant).filter(models.Variant.id == item.variant_id).first() if item.variant_id else None
        out.append({
            "id": item.id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "qty": item.qty,
            "product_name": product.name if product else None,
            "variant_label": variant.label if variant else None,
            "price": variant.price if variant else (product.variants[0].price if product and product.variants else 0),
            "image_url": product.image_url if product else None,
        })
    return out


@router.post("", response_model=schemas.CartItemOut)
def add_cart_item(payload: schemas.CartItemIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).filter(models.Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")

    variant = None
    if payload.variant_id:
        variant = db.query(models.Variant).filter(models.Variant.id == payload.variant_id).first()
        if not variant or variant.product_id != product.id:
            raise HTTPException(400, "Variant noto'g'ri")

    existing = db.query(models.CartItem).filter(
        models.CartItem.telegram_user_id == user["id"],
        models.CartItem.product_id == payload.product_id,
        models.CartItem.variant_id == payload.variant_id,
    ).first()
    if existing:
        existing.qty += payload.qty
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "product_id": existing.product_id,
            "variant_id": existing.variant_id,
            "qty": existing.qty,
            "product_name": product.name,
            "variant_label": variant.label if variant else None,
            "price": variant.price if variant else product.variants[0].price if product.variants else 0,
            "image_url": product.image_url,
        }

    cart_item = models.CartItem(
        telegram_user_id=user["id"],
        product_id=payload.product_id,
        variant_id=payload.variant_id,
        qty=payload.qty,
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return {
        "id": cart_item.id,
        "product_id": cart_item.product_id,
        "variant_id": cart_item.variant_id,
        "qty": cart_item.qty,
        "product_name": product.name,
        "variant_label": variant.label if variant else None,
        "price": variant.price if variant else product.variants[0].price if product.variants else 0,
        "image_url": product.image_url,
    }


@router.patch("/{cart_item_id}")
def update_cart_item(cart_item_id: str, payload: schemas.CartItemIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(models.CartItem).filter(models.CartItem.id == cart_item_id, models.CartItem.telegram_user_id == user["id"]).first()
    if not item:
        raise HTTPException(404, "Mahsulot savatda topilmadi")
    item.qty = payload.qty
    db.commit()
    return {"ok": True}


@router.delete("/{cart_item_id}")
def remove_cart_item(cart_item_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(models.CartItem).filter(models.CartItem.id == cart_item_id, models.CartItem.telegram_user_id == user["id"]).first()
    if not item:
        raise HTTPException(404, "Mahsulot savatda topilmadi")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.delete("")
def clear_cart(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(models.CartItem).filter(models.CartItem.telegram_user_id == user["id"]).delete()
    db.commit()
    return {"ok": True}
