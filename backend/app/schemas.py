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
    category: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
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


class ProductImageIn(BaseModel):
    url: str
    position: Optional[int] = 0


class ProductImageOut(BaseModel):
    id: str
    url: str
    position: int
    class Config:
        from_attributes = True


class ProductSizeGuideIn(BaseModel):
    content: str


class ReviewIn(BaseModel):
    author_name: Optional[str] = None
    text: str = Field(min_length=1, max_length=2000)


class ReviewOut(BaseModel):
    id: str
    product_id: str
    author_name: Optional[str]
    text: str
    created_at: datetime
    class Config:
        from_attributes = True


class RatingIn(BaseModel):
    stars: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    product_id: str
    rating: float
    rating_count: int
    user_stars: int


class FavoriteOut(BaseModel):
    product: ProductOut
    created_at: datetime
    class Config:
        from_attributes = True


class ProductDetailOut(ProductOut):
    images: List[ProductImageOut] = []
    size_guide: Optional[str] = None
    reviews: List[ReviewOut] = []
    is_favorite: bool = False
    views_count: int = 0
    in_cart_count: int = 0


class OrderItemIn(BaseModel):
    variant_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class OrderIn(BaseModel):
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: str = Field(min_length=3, max_length=50)
    customer_address: str = Field(min_length=1, max_length=1000)
    delivery_date: date
    note: Optional[str] = None
    promo_code: Optional[str] = None
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


class OrderStatusEventOut(BaseModel):
    id: str
    status: str
    note: Optional[str]
    created_at: datetime
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
    status_events: List[OrderStatusEventOut] = []
    promo_code: Optional[str] = None
    discount_amount: int = 0
    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str  # yangi | tayyor | yolda | yetkazildi | bekor


class PromoValidIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    order_total: int = Field(ge=0)


class PromoValidOut(BaseModel):
    valid: bool
    code: str
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    min_order_total: int = 0
    discount_amount: int = 0
    message: str = ""


class AnalyticsEventIn(BaseModel):
    event_type: str = Field(min_length=1, max_length=50)
    product_id: Optional[str] = None


class AnalyticsInsightOut(BaseModel):
    most_viewed: List[dict] = []
    most_added_to_cart: List[dict] = []
    most_abandoned: List[dict] = []
    total_views: int = 0
    total_add_to_cart: int = 0
    total_orders: int = 0
    conversion_rate: float = 0


class CartItemIn(BaseModel):
    product_id: str = Field(min_length=1)
    variant_id: Optional[str] = None
    qty: int = Field(default=1, gt=0)


class CartItemOut(BaseModel):
    id: str
    product_id: str
    variant_id: Optional[str]
    qty: int
    product_name: Optional[str] = None
    variant_label: Optional[str] = None
    price: Optional[int] = None
    image_url: Optional[str] = None
    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: str
    telegram_user_id: int
    title: str
    body: str
    kind: str
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True


class LoyaltyOfferIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="")
    offer_type: str = Field(default="percent")
    value: int = Field(ge=0)
    min_total: int = Field(default=0, ge=0)
    active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class LoyaltyOfferOut(LoyaltyOfferIn):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True


class StockAlertOut(BaseModel):
    product_id: str
    product_name: str
    variant_label: str
    stock_qty: int


class StatsOut(BaseModel):
    date: str
    orders_count: int
    revenue: int
    items_sold: int
    top_products: List[dict]
    report_text: str


class AdminCheckOut(BaseModel):
    is_admin: bool
    is_seller: bool = False
    role: Optional[str] = None
    user_id: Optional[int] = None
    full_name: Optional[str] = None

class AdminIn(BaseModel):
    telegram_user_id: int = Field(gt=0)
    full_name: Optional[str] = Field(default=None, max_length=200)
    role: str = Field(default="seller", pattern="^(admin|seller)$")


class AdminOut(BaseModel):
    id: str
    telegram_user_id: int
    full_name: Optional[str]
    role: str = "seller"
    protected: bool = False

    class Config:
        from_attributes = True


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    icon: str = Field(default="✨", max_length=10)
    active: bool = True


class CategoryOut(CategoryIn):
    id: str
    class Config:
        from_attributes = True


class HeroBannerIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    subtitle: str = Field(default="", max_length=500)
    image_url: Optional[str] = None
    button_text: str = Field(default="Mahsulotlarni ko'rish", max_length=100)
    button_link: str = Field(default="", max_length=500)
    active: bool = True


class HeroBannerOut(HeroBannerIn):
    id: str
    class Config:
        from_attributes = True
