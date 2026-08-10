from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import limiter
from .config import settings

app = FastAPI(title="Rate Limiter Service")


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
