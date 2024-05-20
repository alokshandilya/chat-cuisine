from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse
import os
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add a startup event to log the environment variable
@app.on_event("startup")
async def startup_event():
    secret_key = os.getenv("SESSION_SECRET_KEY")
    if not secret_key:
        logger.error("No SESSION_SECRET_KEY set for FastAPI application")
        raise ValueError("No SESSION_SECRET_KEY set for FastAPI application")
    else:
        logger.info("SESSION_SECRET_KEY successfully retrieved")
        # Adding middleware during startup to ensure logging happens before the middleware is added
        app.add_middleware(SessionMiddleware, secret_key=secret_key)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    logger.info("Root endpoint accessed")
    return HTMLResponse(content="Hello, World!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
