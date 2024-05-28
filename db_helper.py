from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    ForeignKey,
    Text,
    DateTime,
    Enum,
    Table,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.sql import func
import enum
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the password from environment variable
db_password = os.getenv("DB_PASSWORD")

# Database connection URL
# DATABASE_URL = "mysql+pymysql://root@localhost/chatcuisine"
DATABASE_URL = f"mysql+pymysql://avnadmin:{db_password}@mysql-chatcuisine.e.aivencloud.com:17612/chatcuisine"

# Create engine and session local
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Association table for many-to-many relationship between orders and food items
order_items = Table(
    "order_items",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("food_item_id", ForeignKey("food_items.id"), primary_key=True),
    Column("quantity", Integer, nullable=False),
)


# User table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", uselist=False, back_populates="user")
    reviews = relationship("Review", back_populates="user")


# FoodItem table
class FoodItem(Base):
    __tablename__ = "food_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    available = Column(Boolean, default=True)
    image_url = Column(String(255), nullable=True)
    orders = relationship("Order", secondary=order_items, back_populates="food_items")


# Order table
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    total_amount = Column(Float, nullable=False)
    user = relationship("User", back_populates="orders")
    food_items = relationship(
        "FoodItem", secondary=order_items, back_populates="orders"
    )
    tracking = relationship(
        "OrderTracking",
        uselist=False,
        back_populates="order",
        cascade="all, delete-orphan",
    )


# Cart table
class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    items = relationship("CartItem", back_populates="cart")
    user = relationship("User", back_populates="cart")


# CartItem table
class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    food_item_id = Column(Integer, ForeignKey("food_items.id"))
    quantity = Column(Integer, nullable=False)
    cart = relationship("Cart", back_populates="items")
    food_item = relationship("FoodItem")


# Review table
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="reviews")
    order = relationship("Order")


# OrderStatusEnum enumeration
class OrderStatusEnum(enum.Enum):
    processing = "processing"
    in_transit = "in-transit"
    delivered = "delivered"


# OrderTracking table
class OrderTracking(Base):
    __tablename__ = "order_tracking"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(
        Enum(OrderStatusEnum), default=OrderStatusEnum.processing, nullable=False
    )
    timestamp = Column(DateTime, server_default=func.now())
    order = relationship("Order", back_populates="tracking")

# Create a session maker
Session = sessionmaker(bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)


# Function to get order status for tracking
def get_order_status(order_id: int) -> str:
    session = SessionLocal()
    try:
        tracking = (
            session.query(OrderTracking)
            .filter(OrderTracking.order_id == order_id)
            .first()
        )
        return tracking.status.value if tracking else None
    finally:
        session.close()


# import os
# from dotenv import load_dotenv
#
# from sqlalchemy import create_engine, Column, Integer, String
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
#
# Base = declarative_base()
#
#
# # Define your OrderTracking table class
# class OrderTracking(Base):
#     __tablename__ = 'order_tracking'
#
#     order_id = Column(Integer, primary_key=True)
#     status = Column(String)
#
#
# # Load environment variables from .env file
# load_dotenv()
#
# # Access the password from environment variable
# db_password = os.getenv("DB_PASSWORD")
#
# # Create an engine using pymysql
# engine = create_engine(
#     f"mysql+mysqlconnector://avnadmin:{db_password}@mysql-chatcuisine.e.aivencloud.com:17612/chatcuisine")
#
#
# # Create a session maker
# Session = sessionmaker(bind=engine)
#
#
# def get_order_status(order_id):
#     # Create a session
#     session = Session()
#
#     # Query the database using SQLAlchemy ORM
#     status = session.query(OrderTracking.status).filter_by(order_id=order_id).scalar()
#
#     session.close()
#
#     return status
