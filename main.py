from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
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
from db_helper import FoodItem, SessionLocal, User
from jose import JWTError, jwt

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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


class WebhookRequest(BaseModel):
    responseId: str
    queryResult: dict


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


def handle_order_add(params: dict, session_id: str):
    return f"Adding {params['item']} to order for session {session_id}"


def handle_order_remove(params: dict, session_id: str):
    return f"Removing {params['item']} from order for session {session_id}"


@app.post("/webhook")
async def webhook_handler(request: WebhookRequest):
    try:
        query_result = request.queryResult
        intent_name = query_result["intent"]["displayName"]
        session_id = (
            query_result.get("outputContexts", [{}])[0].get("name", "").split("/")[-1]
        )

        if intent_name == "order.add":
            params = query_result["parameters"]
            return {"fulfillmentText": handle_order_add(params, session_id)}
        elif intent_name == "order.remove":
            params = query_result["parameters"]
            return {"fulfillmentText": handle_order_remove(params, session_id)}
        elif intent_name == "track.order - context: ongoing-tracking":
            params = query_result["parameters"]
            return {"fulfillmentText": track_order(params)}
        else:
            raise HTTPException(status_code=400, detail="Invalid intent")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")


def track_order(params: dict):
    order_id = int(params["number"])
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
