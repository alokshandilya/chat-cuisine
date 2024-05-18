import os
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


# Define your OrderTracking table class
class OrderTracking(Base):
    __tablename__ = 'order_tracking'

    order_id = Column(Integer, primary_key=True)
    status = Column(String)


# Load environment variables from .env file
load_dotenv()

# Access the password from environment variable
db_password = os.getenv("DB_PASSWORD")

# Create an engine using pymysql
engine = create_engine(
    f"mysql+mysqlconnector://avnadmin:{db_password}@mysql-chatcuisine.e.aivencloud.com:17612/chatcuisine")


# Create a session maker
Session = sessionmaker(bind=engine)


def get_order_status(order_id):
    # Create a session
    session = Session()

    # Query the database using SQLAlchemy ORM
    status = session.query(OrderTracking.status).filter_by(order_id=order_id).scalar()

    session.close()

    return status
