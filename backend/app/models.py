import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Date, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base

def gen_id():
    return str(uuid.uuid4())

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # 'kiyim' | 'parfyum'
    emoji = Column(String, default="👗")
    description = Column(Text, default="")
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    variants = relationship("Variant", back_populates="product", cascade="all, delete-orphan")
    ratings = relationship("ProductRating", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position")
    size_guide = relationship("ProductSizeGuide", back_populates="product", cascade="all, delete-orphan", uselist=False)
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")


class Variant(Base):
    __tablename__ = "variants"
    id = Column(String, primary_key=True, default=gen_id)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    label = Column(String, nullable=False)     # "M", "50ml" va h.k.
    color = Column(String, nullable=True)
    price = Column(Integer, nullable=False)
    stock_qty = Column(Integer, default=0)

    product = relationship("Product", back_populates="variants")


class ProductRating(Base):
    __tablename__ = "product_ratings"
    __table_args__ = (UniqueConstraint("product_id", "telegram_user_id", name="uq_product_rating_user"),)

    id = Column(String, primary_key=True, default=gen_id)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    telegram_user_id = Column(BigInteger, nullable=False)
    stars = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="ratings")


class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(String, primary_key=True, default=gen_id)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    position = Column(Integer, default=0)
    product = relationship("Product", back_populates="images")


class ProductSizeGuide(Base):
    __tablename__ = "product_size_guides"
    product_id = Column(String, ForeignKey("products.id"), primary_key=True)
    content = Column(Text, nullable=False, default="")
    product = relationship("Product", back_populates="size_guide")


class ProductReview(Base):
    __tablename__ = "product_reviews"
    __table_args__ = (UniqueConstraint("product_id", "telegram_user_id", name="uq_product_review_user"),)
    id = Column(String, primary_key=True, default=gen_id)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    telegram_user_id = Column(BigInteger, nullable=False)
    author_name = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="reviews")


class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_address = Column(Text, nullable=False)
    delivery_date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    total = Column(Integer, nullable=False)
    status = Column(String, default="yangi")  # yangi, tayyor, yolda, yetkazildi, bekor
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_events = relationship("OrderStatusEvent", back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusEvent.created_at")
    promotion = relationship("OrderPromotion", back_populates="order", cascade="all, delete-orphan", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(String, primary_key=True, default=gen_id)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    variant_id = Column(String, ForeignKey("variants.id"), nullable=True)
    product_name = Column(String, nullable=False)
    variant_label = Column(String, nullable=False)
    color = Column(String, nullable=True)
    price = Column(Integer, nullable=False)
    qty = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    id = Column(String, primary_key=True, default=gen_id)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(String, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    order = relationship("Order", back_populates="status_events")


class PromoCode(Base):
    __tablename__ = "promo_codes"
    id = Column(String, primary_key=True, default=gen_id)
    code = Column(String, unique=True, nullable=False, index=True)
    discount_type = Column(String, nullable=False, default="percent")  # percent | fixed
    discount_value = Column(Integer, nullable=False)
    min_order_total = Column(Integer, default=0)
    usage_limit = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    active = Column(Integer, default=1)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrderPromotion(Base):
    __tablename__ = "order_promotions"
    id = Column(String, primary_key=True, default=gen_id)
    order_id = Column(String, ForeignKey("orders.id"), unique=True, nullable=False)
    code = Column(String, nullable=False)
    discount_amount = Column(Integer, nullable=False, default=0)
    order = relationship("Order", back_populates="promotion")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("telegram_user_id", "product_id", name="uq_favorite_user_product"),)
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("telegram_user_id", "product_id", "variant_id", name="uq_cart_user_product_variant"),)
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(String, ForeignKey("variants.id"), nullable=True, index=True)
    qty = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product")
    variant = relationship("Variant")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False, default="")
    kind = Column(String, nullable=False, default="info")
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class LoyaltyOffer(Base):
    __tablename__ = "loyalty_offers"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    offer_type = Column(String, nullable=False, default="percent")
    value = Column(Integer, nullable=False, default=0)
    min_total = Column(Integer, default=0)
    active = Column(Integer, default=1)
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Admin(Base):
    __tablename__ = "admins"
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="admin")  # admin | seller
    added_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    icon = Column(String, default="✨")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class HeroBanner(Base):
    __tablename__ = "hero_banners"
    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False)
    subtitle = Column(Text, default="")
    image_url = Column(String, nullable=True)
    button_text = Column(String, default="Mahsulotlarni ko'rish")
    button_link = Column(String, default="")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
