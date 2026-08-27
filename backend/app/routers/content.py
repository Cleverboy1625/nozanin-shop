from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(tags=["content"])


@router.get("/api/categories", response_model=list[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).filter(models.Category.active == 1).order_by(models.Category.created_at.asc()).all()


@router.post("/api/categories", response_model=schemas.CategoryOut, status_code=201)
def create_category(payload: schemas.CategoryIn, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if db.query(models.Category).filter((models.Category.slug == payload.slug) | (models.Category.name == payload.name)).first():
        raise HTTPException(409, "Bu kategoriya allaqachon mavjud")
    category = models.Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/api/categories/{category_id}", response_model=schemas.CategoryOut)
def update_category(category_id: str, payload: schemas.CategoryIn, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    category = db.query(models.Category).get(category_id)
    if not category:
        raise HTTPException(404, "Kategoriya topilmadi")
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/api/categories/{category_id}")
def delete_category(category_id: str, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    category = db.query(models.Category).get(category_id)
    if not category:
        raise HTTPException(404, "Kategoriya topilmadi")
    category.active = 0
    db.commit()
    return {"ok": True}


@router.get("/api/hero", response_model=schemas.HeroBannerOut | None)
def get_hero(db: Session = Depends(get_db)):
    return db.query(models.HeroBanner).filter(models.HeroBanner.active == 1).order_by(models.HeroBanner.created_at.desc()).first()


@router.put("/api/hero", response_model=schemas.HeroBannerOut)
def upsert_hero(payload: schemas.HeroBannerIn, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    hero = db.query(models.HeroBanner).order_by(models.HeroBanner.created_at.desc()).first()
    if not hero:
        hero = models.HeroBanner()
        db.add(hero)
    for key, value in payload.model_dump().items():
        setattr(hero, key, value)
    db.commit()
    db.refresh(hero)
    return hero


@router.delete("/api/hero")
def delete_hero(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    db.query(models.HeroBanner).update({models.HeroBanner.active: 0})
    db.commit()
    return {"ok": True}