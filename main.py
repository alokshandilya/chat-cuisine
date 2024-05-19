from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# Secret key for session management
app.add_middleware(SessionMiddleware, secret_key='your_secret_key')

templates = Jinja2Templates(directory="templates")

# Mock user database
fake_users_db = {
    "testuser": {"username": "testuser", "password": "testpassword"}
}

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
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
