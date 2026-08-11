from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import limiter
from .config import settings

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Rate Limiter Service")

# The dashboard is served by one instance but calls all three (different
# ports = different origins from the browser's point of view), so every
# instance needs to accept cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class CheckIn(BaseModel):
    key: str
    algorithm: str = "token_bucket"
    limit: int = settings.default_limit
    window_seconds: float = settings.default_window_seconds


@app.post("/check")
async def check(body: CheckIn):
    try:
        result = await limiter.check(body.algorithm, body.key, body.limit, body.window_seconds)
    except ValueError as e:
        raise HTTPException(400, str(e))
    result["instance"] = settings.instance_name
    return result


@app.get("/health")
def health():
    return {"status": "ok", "instance": settings.instance_name}


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")