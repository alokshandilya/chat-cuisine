from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import db_helper
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
        logger.error(f"Error processing webhook: {e}")
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


@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/", status_code=302)


@app.get("/index", response_class=HTMLResponse)
async def read_root(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/google721ed54125969664.html", response_class=HTMLResponse)
async def serve_verification_file():
    return HTMLResponse(content="google-site-verification: google721ed54125969664.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
