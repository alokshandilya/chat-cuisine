import mysql.connector
global conn

# Connect to your MySQL database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="pandeyji_eatery"
)

def get_order_status(order_id):
    # Create a cursor object
    cursor = conn.cursor()

    # Execute the query
    cursor.execute("SELECT status FROM order_tracking WHERE order_id = %s", (order_id,))

    # Fetch the status
    status = cursor.fetchone()

    if status:
        return status[0]  # Return the status value
    else:
        return None  # Return None if no status found