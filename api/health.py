# Vercel serverless function for health check
# Returns a simple JSON indicating the service is up.

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def health():
    return JSONResponse(content={"status": "ok"})
