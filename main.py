from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()

PORT = int(os.getenv("PORT", 8000))
HOST = "localhost"

if __name__ == "__main__":
    uvicorn.run("app:app", host=HOST, port=PORT, reload=True)
