import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin, require_staff, get_current_user
from ..report_service import send_product_post

router = APIRouter(prefix="/api/products", tags=["products"])

SPLIT_CHARS = [",", ";"]


def _split_vals(s: Optional[str]):
    if not s:
        return []
    for ch in SPLIT_CHARS:
        if ch in s:
            return [x.strip() for x in s.split(ch) if x.strip()]
    return [s.strip()]


def product_base_dict(product, db: Session, user=None) -> dict:
    fav = False
    if user:
        fav = db.query(models.Favorite).filter(
            models.Favorite.telegram_user_id == user["id"],
            models.Favorite.product_id == product.id,
        ).first() is not None
    return {
        "id": product.id, "name": product.name, "category": product.category,
        "emoji": product.emoji, "description": product.description,
        "image_url": product.image_url, "variants": product.variants,
        "rating": round(db.query(func.avg(models.ProductRating.stars)).filter(
            models.ProductRating.product_id == product.id
        ).scalar() or 0, 1),
        "rating_count": db.query(models.ProductRating).filter(
            models.ProductRating.product_id == product.id
        ).count(),
        "is_favorite": fav,
    }


@router.get("", response_model=List[schemas.ProductOut])
def list_products(
    category: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    sizes: Optional[str] = None,
    colors: Optional[str] = None,
    in_stock: Optional[bool] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Product)
    if category and category != "hammasi":
        q = q.filter(models.Product.category == category)

    products = q.options(joinedload(models.Product.variants)).order_by(models.Product.created_at.desc()).all()

    size_list = set(_split_vals(sizes))
    color_list = set(_split_vals(colors))

    def price_ok(p):
        if min_price is None and max_price is None:
            return True
        prices = [v.price for v in p.variants]
        return (min_price is None or any(pr >= min_price for pr in prices)) and \
               (max_price is None or any(pr <= max_price for pr in prices))

    def size_ok(p):
        if not size_list:
            return True
        return any(v.label in size_list for v in p.variants)

    def color_ok(p):
        if not color_list:
            return True
        return any(v.color in color_list for v in p.variants if v.color)

    def stock_ok(p):
        if in_stock is None:
            return True
        has = any(v.stock_qty > 0 for v in p.variants)
        return has if in_stock else not has

    filtered = [p for p in products if price_ok(p) and size_ok(p) and color_ok(p) and stock_ok(p)]

    if sort == "cheap":
        filtered.sort(key=lambda p: min(v.price for v in p.variants))
    elif sort == "popular":
        def popularity(p):
            cnt = db.query(models.ProductRating).filter(models.ProductRating.product_id == p.id).count()
            avg = db.query(func.avg(models.ProductRating.stars)).filter(
                models.ProductRating.product_id == p.id
            ).scalar() or 0
            return (cnt, avg)
        filtered.sort(key=popularity, reverse=True)
    # 'new' yoki default — created_at desc (allaqachon shunday)

    return [product_base_dict(p, db) for p in filtered]


@router.get("/{product_id}", response_model=schemas.ProductDetailOut)
def get_product_detail(product_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).options(
        joinedload(models.Product.variants),
        joinedload(models.Product.images),
        joinedload(models.Product.reviews),
    ).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")

    # view event avtomatik
    db.add(models.AnalyticsEvent(
        telegram_user_id=user["id"], event_type="view", product_id=product.id,
    ))
    db.commit()

    fav = db.query(models.Favorite).filter(
        models.Favorite.telegram_user_id == user["id"],
        models.Favorite.product_id == product.id,
    ).first() is not None

    views_count = db.query(func.count(models.AnalyticsEvent.id)).filter(
        models.AnalyticsEvent.event_type == "view",
        models.AnalyticsEvent.product_id == product.id,
    ).scalar() or 0
    in_cart_count = db.query(func.count(models.AnalyticsEvent.id)).filter(
        models.AnalyticsEvent.event_type == "add_to_cart",
        models.AnalyticsEvent.product_id == product.id,
    ).scalar() or 0

    size_guide = db.query(models.ProductSizeGuide).filter(
        models.ProductSizeGuide.product_id == product.id
    ).first()

    return {
        "id": product.id, "name": product.name, "category": product.category,
        "emoji": product.emoji, "description": product.description,
        "image_url": product.image_url, "variants": product.variants,
        "rating": round(db.query(func.avg(models.ProductRating.stars)).filter(
            models.ProductRating.product_id == product.id
        ).scalar() or 0, 1),
        "rating_count": db.query(models.ProductRating).filter(
            models.ProductRating.product_id == product.id
        ).count(),
        "images": product.images,
        "size_guide": size_guide.content if size_guide else None,
        "reviews": product.reviews,
        "is_favorite": fav,
        "views_count": views_count,
        "in_cart_count": in_cart_count,
    }


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


@router.post("/{product_id}/reviews", response_model=schemas.ReviewOut, status_code=201)
def create_review(product_id: str, payload: schemas.ReviewIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    name = payload.author_name or f"Foydalanuvchi {user['id']}"
    existing = db.query(models.ProductReview).filter(
        models.ProductReview.product_id == product_id,
        models.ProductReview.telegram_user_id == user["id"],
    ).first()
    if existing:
        existing.text = payload.text
        existing.author_name = name
        db.commit()
        db.refresh(existing)
        return existing
    review = models.ProductReview(
        product_id=product_id,
        telegram_user_id=user["id"],
        author_name=name,
        text=payload.text,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@router.get("/{product_id}/reviews", response_model=List[schemas.ReviewOut])
def list_reviews(product_id: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    return db.query(models.ProductReview).filter(
        models.ProductReview.product_id == product_id
    ).order_by(models.ProductReview.created_at.desc()).all()


@router.post("", response_model=schemas.ProductOut)
def create_product(payload: schemas.ProductIn, db: Session = Depends(get_db), admin=Depends(require_staff)):
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


@router.post("/{product_id}/images", response_model=schemas.ProductImageOut)
def add_product_image(product_id: str, payload: schemas.ProductImageIn, db: Session = Depends(get_db), admin=Depends(require_staff)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    image = models.ProductImage(product_id=product_id, url=payload.url, position=payload.position or 0)
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.delete("/{product_id}/images/{image_id}")
def delete_product_image(product_id: str, image_id: str, db: Session = Depends(get_db), admin=Depends(require_staff)):
    image = db.query(models.ProductImage).filter(
        models.ProductImage.id == image_id,
        models.ProductImage.product_id == product_id,
    ).first()
    if not image:
        raise HTTPException(404, "Qo'shimcha rasm topilmadi")
    db.delete(image)
    db.commit()
    return {"ok": True}


@router.post("/{product_id}/size-guide")
def set_size_guide(product_id: str, payload: schemas.ProductSizeGuideIn, db: Session = Depends(get_db), admin=Depends(require_staff)):
    product = db.query(models.Product).get(product_id)
    if not product:
        raise HTTPException(404, "Mahsulot topilmadi")
    guide = db.query(models.ProductSizeGuide).filter(
        models.ProductSizeGuide.product_id == product_id
    ).first()
    if guide:
        guide.content = payload.content
    else:
        guide = models.ProductSizeGuide(product_id=product_id, content=payload.content)
        db.add(guide)
    db.commit()
    return {"ok": True, "size_guide": payload.content}


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db), admin=Depends(require_staff)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Faqat rasm yuklash mumkin")

    frontend_candidates = (
        Path(__file__).resolve().parents[2] / "frontend",
        Path(__file__).resolve().parents[3] / "frontend",
    )
    frontend_dir = next((path for path in frontend_candidates if path.is_dir()), None)
    if not frontend_dir:
        raise HTTPException(500, "frontend papka topilmadi")

    img_dir = frontend_dir / "product-images"
    img_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
        ext = ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = img_dir / filename
    content = await file.read()
    dest.write_bytes(content)

    return {"ok": True, "url": f"/product-images/{filename}"}


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: str, payload: schemas.ProductIn, db: Session = Depends(get_db), admin=Depends(require_staff)):
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
    # Buyurtma tarixi saqlanadi, faqat endi mavjud bo'lmagan variantga havola uziladi.
    variant_ids = [variant.id for variant in product.variants]
    if variant_ids:
        db.query(models.OrderItem).filter(models.OrderItem.variant_id.in_(variant_ids)).update(
            {models.OrderItem.variant_id: None}, synchronize_session=False
        )
    db.query(models.Favorite).filter(models.Favorite.product_id == product_id).delete(synchronize_session=False)
    db.query(models.CartItem).filter(models.CartItem.product_id == product_id).delete(synchronize_session=False)
    db.query(models.AnalyticsEvent).filter(models.AnalyticsEvent.product_id == product_id).delete(synchronize_session=False)
    db.delete(product)
    db.commit()
    return {"ok": True}
