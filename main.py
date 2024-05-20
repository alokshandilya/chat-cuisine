from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import db_helper
import os
import logging

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the secret key from environment variables
SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No SESSION_SECRET_KEY set for Flask application")

# Add the SessionMiddleware with the secret key
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)


class WebhookRequest(BaseModel):
    responseId: str
    queryResult: dict


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

fake_users_db = {"testuser": {"username": "testuser", "password": "testpassword"}}


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    user = request.session.get("user")
    if user:
        return RedirectResponse("/index", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = fake_users_db.get(username)
    if user and user["password"] == password:
        request.session["user"] = user["username"]
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
