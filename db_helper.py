import os
from dotenv import load_dotenv

import pymysql
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

timeout = 10
connection = pymysql.connect(
    charset="utf8mb4",
    connect_timeout=timeout,
    cursorclass=pymysql.cursors.DictCursor,
    db=os.getenv("DB_NAME"),
    host=os.getenv("DB_HOST"),
    password=os.getenv("DB_PASS"),
    read_timeout=timeout,
    port=int(os.getenv("DB_PORT")),
    user=os.getenv("DB_USER"),
    write_timeout=timeout,
)

# Create an engine using pymysql
engine = create_engine(
    "mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")

# Create a session maker
Session = sessionmaker(bind=engine)


def get_order_status(order_id):
    # Create a session
    session = Session()

    # Query the database using SQLAlchemy ORM
    status = session.query(OrderTracking.status).filter_by(order_id=order_id).scalar()

    session.close()

    return status