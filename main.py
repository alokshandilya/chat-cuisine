from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os
import logging
from passlib.context import CryptContext
import db_helper
import generic_helper
from db_helper import FoodItem, SessionLocal, User
from jose import JWTError, jwt

app = FastAPI()
templates = Jinja2Templates(directory="templates")
inprogress_orders = {}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the secret key from environment variables
load_dotenv()
SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No SESSION_SECRET_KEY set for Flask application")

# Add the SessionMiddleware with the secret key
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# JWT token related functions
def create_jwt_token(username: str, role: str) -> str:
    payload = {"sub": username, "role": role}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def decode_jwt_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request):
    token = request.session.get("token")
    if token:
        try:
            payload = decode_jwt_token(token)
            username = payload.get("sub")
            role = payload.get("role")
            return username, role
        except JWTError as e:
            raise HTTPException(status_code=401, detail="Invalid token")
    return None, None


# Restrict access to admin-only endpoints
def admin_only(request: Request):
    _, role = get_current_user(request)
    if role != "admin":
        raise HTTPException(
            status_code=403, detail="Only admins can access this feature"
        )


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# Define your get_db function to obtain a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/webhook")
async def handle_request(request: Request):
    # Retrieve the JSON data from the request
    payload = await request.json()

    # Extract the necessary information from the payload
    # based on the structure of the WebhookRequest from Dialogflow
    intent = payload["queryResult"]["intent"]["displayName"]
    parameters = payload["queryResult"]["parameters"]
    output_contexts = payload["queryResult"]["outputContexts"]
    session_id = generic_helper.extract_session_id(output_contexts[0]["name"])

    intent_handler_dict = {
        "order.add - context: ongoing-order": add_to_order,
        "order.remove - context: ongoing-order": remove_from_order,
        "order.complete - context: ongoing-order": complete_order,
        "track.order - context: ongoing-tracking": track_order,
    }

    return intent_handler_dict[intent](parameters, session_id)


def save_to_db(order_items: dict):
    next_order_id = db_helper.get_next_order_id()

    # Insert individual items along with quantity in order_items table
    for food_item, quantity in order_items.items():
        rcode = db_helper.insert_order_item(food_item, quantity, next_order_id)
        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "Order Received, it's in processing")
    return next_order_id


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        fullfillmentText = "I am having trouble finding your order"
    else:
        order = inprogress_orders[session_id]
        order_id = save_to_db(order)
        if order_id == -1:
            fullfillment_text = (
                "Sorry, I couldn't process your order due to a backend error. "
                "Please place a new order again"
            )
        else:
            order_total = db.helper.get_total_order_price(order_id)
            fullfillment_text = (
                f"Order placed successfully! Your order id is: {order_id}. "
                "Your total order amount is: {order_total}"
            )
        del inprogress_orders[session_id]
    return JSONResponse(content={"fulfillmentText": fullfillment_text})


def add_to_order(parameters: dict, session_id: str):
    food_items = parameters["food-item"]
    quantities = parameters["number"]

    if len(food_items) != len(quantities):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_food_dict = dict(zip(food_items, quantities))

        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict

        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(
            content={
                "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
            }
        )

    food_items = parameters["food-item"]
    current_order = inprogress_orders[session_id]

    removed_items = []
    no_such_items = []

    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]

    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = (
            f' Your current order does not have {",".join(no_such_items)}'
        )

    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        order_str = generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    return JSONResponse(content={"fulfillmentText": fulfillment_text})


def track_order(parameters: dict):
    order_id = int(parameters["number"])
    order_status = db_helper.get_order_status(order_id)
    if order_status:
        fullfillmentText = (
            f"Your order status for order id {order_id} is: {order_status}"
        )
    else:
        fullfillmentText = f"Sorry, no order found for order id: {order_id}"
    return fullfillmentText


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    user = request.session.get("user")
    is_admin = request.session.get("is_admin")
    if user:
        if is_admin:
            return RedirectResponse("/admin", status_code=302)
        return RedirectResponse("/index", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.hashed_password):
        request.session["user"] = user.username
        request.session["is_admin"] = user.is_admin
        role = "admin" if user.is_admin else "user"
        token = create_jwt_token(user.username, role)
        request.session["token"] = token  # Store the token in the session
        if user.is_admin:
            return RedirectResponse("/admin", status_code=302)
        return RedirectResponse("/index", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid credentials"}
    )


def get_current_admin_user(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    return user


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


@app.get("/index", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    if not username:
        return RedirectResponse("/", status_code=302)

    user = db.query(User).filter(User.username == username).first()
    full_name = user.full_name if user else None

    food_items = db.query(FoodItem).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": username,
            "full_name": full_name,
            "food_items": food_items,
        },
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    is_admin = request.session.get("is_admin")
    if not username or not is_admin:
        return RedirectResponse("/", status_code=302)

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_admin:
        return RedirectResponse("/", status_code=302)

    return templates.TemplateResponse(
        "admin_dashboard.html", {"request": request, "full_name": user.full_name}
    )


@app.get("/create-food-item", response_class=HTMLResponse)
async def create_food_item_form(request: Request):
    admin_only(request)
    return templates.TemplateResponse("create_food_item.html", {"request": request})


@app.post("/create-food-item", response_class=HTMLResponse)
async def create_food_item(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    price: float = Form(...),
    image_url: str = Form(...),
    db: Session = Depends(get_db),
):
    admin_only(request)
    image_path = f"/static/images/{image_url}"
    new_food_item = FoodItem(
        name=name, description=description, price=price, image_url=image_path
    )
    db.add(new_food_item)
    db.commit()
    db.refresh(new_food_item)
    return RedirectResponse(url="/food-items", status_code=303)


@app.post("/remove-food-item/{item_id}")
async def remove_food_item(
    request: Request, item_id: int, db: Session = Depends(get_db)
):
    admin_only(request)
    food_item = db.query(FoodItem).filter(FoodItem.id == item_id).first()
    if food_item:
        db.delete(food_item)
        db.commit()
    return RedirectResponse(url="/food-items", status_code=303)


@app.get("/food-items", response_class=HTMLResponse)
def list_food_items(request: Request, db: Session = Depends(get_db)):
    food_items = db.query(FoodItem).all()
    return templates.TemplateResponse(
        "food_items.html", {"request": request, "food_items": food_items}
    )


@app.get(
    "/create-user", response_class=HTMLResponse, dependencies=[Depends(admin_only)]
)
async def create_user_form(request: Request):
    return templates.TemplateResponse("create_user.html", {"request": request})


@app.post(
    "/create-user", response_class=HTMLResponse, dependencies=[Depends(admin_only)]
)
async def create_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
):
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return RedirectResponse("/admin", status_code=302)


@app.get("/google721ed54125969664.html", response_class=HTMLResponse)
async def serve_verification_file():
    return HTMLResponse(content="google-site-verification: google721ed54125969664.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
