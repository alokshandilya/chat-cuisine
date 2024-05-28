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


# Create a session maker
Session = sessionmaker(bind=engine)


def get_order_status(order_id):
    # Create a session
    session = Session()

    # Query the database using SQLAlchemy ORM
    status = session.query(OrderTracking.status).filter_by(order_id=order_id).scalar()

    session.close()

    return status
