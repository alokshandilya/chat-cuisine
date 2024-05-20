from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse
import os
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the secret key from environment variables
SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
if not SECRET_KEY:
    logger.error("No SESSION_SECRET_KEY set for FastAPI application")
    raise ValueError("No SESSION_SECRET_KEY set for FastAPI application")
else:
    logger.info(f"SESSION_SECRET_KEY successfully retrieved")

# Add the SessionMiddleware with the secret key
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return HTMLResponse(content="Hello, World!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
