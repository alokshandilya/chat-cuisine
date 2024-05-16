from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


# Define your OrderTracking table class
class OrderTracking(Base):
    __tablename__ = 'order_tracking'

    order_id = Column(Integer, primary_key=True)
    status = Column(String)


# Create an engine
engine = create_engine(
    "mysql+mysqlconnector://root:@localhost/chatcuisine")

# Create a session maker
Session = sessionmaker(bind=engine)


def get_order_status(order_id):
    # Create a session
    session = Session()

    # Query the database using SQLAlchemy ORM
    status = session.query(OrderTracking.status).filter_by(order_id=order_id).scalar()

    session.close()

    return status
