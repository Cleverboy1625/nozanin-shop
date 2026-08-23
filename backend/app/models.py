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


class Admin(Base):
    __tablename__ = "admins"
    id = Column(String, primary_key=True, default=gen_id)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)
