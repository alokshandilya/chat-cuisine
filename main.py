from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Point to the templates folder
templates = Jinja2Templates(directory="templates")


# @app.get("/")
# async def root():
#     return {"message": "Hello World"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Render index.html template
    return templates.TemplateResponse("index.html", {"request": request})


# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}