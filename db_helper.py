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
    text,
)
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.sql import func
import enum
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Access the password from environment variable
db_password = os.getenv("DB_PASSWORD")

# Create an engine using pymysql
engine = create_engine(
    f"mysql+mysqlconnector://avnadmin:{db_password}@mysql-chatcuisine.e.aivencloud.com:17612/chatcuisine"
    # f"mysql+mysqlconnector://root@localhost/chatcuisine"
)

# Create engine and session local
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
    order_id = Column(Integer, ForeignKey("orders.id"), primary_key=True, index=True)
    status = Column(
        Enum(OrderStatusEnum), default=OrderStatusEnum.processing, nullable=False
    )
    timestamp = Column(DateTime, server_default=func.now())
    order = relationship("Order", back_populates="tracking")


# Create all tables
Base.metadata.create_all(bind=engine)

# Function to create a new order
def create_order(user_id, total_amount):
    try:
        with engine.connect() as connection:
            # Insert a new order
            connection.execute(
                text("""
                    INSERT INTO orders (user_id, created_at, total_amount)
                    VALUES (:user_id, :created_at, :total_amount)
                """),
                {
                    "user_id": user_id,
                    "created_at": datetime.now(),
                    "total_amount": total_amount,
                }
            )
            # Get the id of the newly created order
            order_id = connection.execute(
                text("SELECT LAST_INSERT_ID()")
            ).fetchone()[0]

            print(f"Order created successfully with ID: {order_id}")
            return order_id
    except Exception as e:
        print(f"An error occurred while creating order: {e}")
        return None



def create_get_total_order_price_function():
    create_function_sql = """
    CREATE FUNCTION get_total_order_price(order_id INT) 
    RETURNS DECIMAL(10, 2)
    DETERMINISTIC
    BEGIN
        DECLARE total_price DECIMAL(10, 2);

        SELECT SUM(oi.quantity * f.price) INTO total_price
        FROM order_items oi
        JOIN food_items f ON oi.food_item_id = f.id
        WHERE oi.order_id = order_id;

        RETURN IFNULL(total_price, 0.00);
    END
    """

    try:
        with engine.connect() as connection:
            for statement in create_function_sql.split("DELIMITER ;"):
                connection.execute(text(statement.strip()))
            print("Function get_total_order_price created successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")


def create_insert_order_item_function():
    # Remove the delimiter commands as they are not needed in Python execution
    create_procedure_sql_cleaned = """
    CREATE PROCEDURE insert_order_item(
        IN p_food_item_id INT,
        IN p_quantity INT,
        IN p_order_id INT
    )
    BEGIN
        INSERT INTO order_items (food_item_id, quantity, order_id)
        VALUES (p_food_item_id, p_quantity, p_order_id);
    END
    """

    try:
        with engine.connect() as connection:
            connection.execute(text(create_procedure_sql_cleaned))
            print("Stored procedure insert_order_item created successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")


# Function to call the MySQL stored procedure and insert an order item
def insert_order_item(food_item, quantity, order_id):
    try:
        with engine.connect() as connection:
            # Begin a transaction
            trans = connection.begin()
            try:
                # Fetching the food_item_id from the food_items table
                result = connection.execute(
                    text("SELECT id FROM food_items WHERE name = :food_item"),
                    {"food_item": food_item},
                ).fetchone()

                if result is None:
                    print(f"Food item '{food_item}' not found in the database")
                    return -1

                food_item_id = result[0]

                # Calling the stored procedure with the fetched id
                connection.execute(
                    text("CALL insert_order_item(:food_item_id, :quantity, :order_id)"),
                    {
                        "food_item_id": food_item_id,
                        "quantity": quantity,
                        "order_id": order_id,
                    },
                )
                # Committing the changes
                trans.commit()
                print("Order item inserted successfully")
                return 1
            except Exception as e:
                # Rolling back the transaction in case of an error
                trans.rollback()
                print(f"An error occurred during transaction: {e}")
                return -1
    except Exception as e:
        print(f"An error occurred: {e}")
        return -1


# Function to insert a record into the order_tracking table
def insert_order_tracking(order_id, status):
    try:
        with engine.connect() as connection:
            # Begin a transaction
            trans = connection.begin()
            try:
                # Inserting the record into the order_tracking table
                insert_query = "INSERT INTO order_tracking (order_id, status) VALUES (:order_id, :status)"
                connection.execute(
                    text(insert_query), {"order_id": order_id, "status": status}
                )
                # Committing the transaction
                trans.commit()
                print("Order tracking inserted successfully!")
            except Exception as e:
                # Rollback the transaction in case of an error
                trans.rollback()
                print(f"An error occurred during transaction: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def get_total_order_price(order_id):
    try:
        with engine.connect() as connection:
            # Executing the SQL query to get the total order price
            query = text("SELECT get_total_order_price(:order_id)")
            result = connection.execute(query, {"order_id": order_id}).fetchone()[0]
            return result
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_next_order_id():
    try:
        with engine.connect() as connection:
            # Executing the SQL query to get the next available order_id
            query = text("SELECT MAX(id) FROM orders")
            result = connection.execute(query).fetchone()[0]
            # Returning the next available order_id
            return 1 if result is None else result + 1
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_order_status(order_id):
    try:
        with engine.connect() as connection:
            # Executing the SQL query to fetch the order status
            query = text("SELECT status FROM order_tracking WHERE order_id = :order_id")
            result = connection.execute(query, {"order_id": order_id}).fetchone()
            # Returning the order status
            return result[0] if result else None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


if __name__ == "__main__":
    # create_get_total_order_price_function()
    # print(get_total_order_price(56))
    # create_insert_order_item_function()
    # insert_order_item(1, 3, 1)
    insert_order_item('Pav Bhaji', 4, 2)
    # insert_order_tracking(1, "processing")
    # print(get_next_order_id())
