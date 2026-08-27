from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/products")
def search_products(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    db: Session = Depends(get_db),
):
    products = db.query(models.Product).join(models.Variant).all()
    filtered = []
    query = (q or "").strip().lower()
    for product in products:
        if query and query not in product.name.lower() and query not in (product.description or "").lower():
            continue
        if category and category != "hammasi" and product.category != category:
            continue
        variants = product.variants
        if min_price is not None and not any(v.price >= min_price for v in variants):
            continue
        if max_price is not None and not any(v.price <= max_price for v in variants):
            continue
        if size and not any(v.label == size for v in variants):
            continue
        if color and not any((v.color or "").lower() == color.lower() for v in variants):
            continue
        filtered.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "image_url": product.image_url,
            "price": min(v.price for v in variants) if variants else 0,
            "rating": round(db.query(func.avg(models.ProductRating.stars)).filter(models.ProductRating.product_id == product.id).scalar() or 0, 1),
        })
    return filtered
