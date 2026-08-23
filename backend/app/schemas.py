from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class VariantIn(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    color: Optional[str] = None
    price: int = Field(gt=0)
    stock_qty: int = Field(default=0, ge=0)


class VariantOut(VariantIn):
    id: str
    class Config:
        from_attributes = True


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(pattern="^(kiyim|parfyum)$")
    emoji: Optional[str] = "👗"
    description: Optional[str] = ""
    image_url: Optional[str] = None
    variants: List[VariantIn]


class ProductOut(BaseModel):
    id: str
    name: str
    category: str
    emoji: str
    description: str
    image_url: Optional[str]
    variants: List[VariantOut]
    rating: float = 0
    rating_count: int = 0
    class Config:
        from_attributes = True


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    product_id: str
    rating: float
    rating_count: int
    user_stars: int


class OrderItemIn(BaseModel):
    variant_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class OrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: str = Field(min_length=3, max_length=50)
    customer_address: str = Field(min_length=1, max_length=1000)
    delivery_date: date
    note: Optional[str] = None
    items: List[OrderItemIn]


class OrderItemOut(BaseModel):
    id: str
    product_name: str
    variant_label: str
    color: Optional[str]
    price: int
    qty: int
    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    telegram_user_id: int
    customer_name: str
    customer_phone: str
    customer_address: str
    delivery_date: date
    note: Optional[str]
    total: int
    status: str
    created_at: datetime
    items: List[OrderItemOut]
    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str  # yangi | tayyor | yolda | yetkazildi | bekor


class StatsOut(BaseModel):
    date: str
    orders_count: int
    revenue: int
    items_sold: int
    top_products: List[dict]
    report_text: str


class AdminCheckOut(BaseModel):
    is_admin: bool
    user_id: Optional[int] = None
    full_name: Optional[str] = None

class AdminIn(BaseModel):
    telegram_user_id: int = Field(gt=0)
    full_name: Optional[str] = Field(default=None, max_length=200)


class AdminOut(BaseModel):
    id: str
    telegram_user_id: int
    full_name: Optional[str]

    class Config:
        from_attributes = True
