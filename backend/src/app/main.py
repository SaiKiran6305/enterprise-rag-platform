import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis import Redis

from app.api.routes import auth, chat, documents, health, search, usage
from app.core.config import get_settings

settings = get_settings()
if settings.environment == "production" and (not settings.jwt_secret or len(settings.jwt_secret) < 32 or not settings.openai_api_key or not settings.cookie_secure):
    raise RuntimeError("Production requires JWT_SECRET (32+ chars), OPENAI_API_KEY, and COOKIE_SECURE=true")
if not settings.jwt_secret:
    raise RuntimeError("JWT_SECRET must be configured")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title=settings.app_name, version=settings.app_version, debug=settings.debug)


@app.get("/health", include_in_schema=False)
def health_root():
    return {"status": "healthy"}


@app.middleware("http")
async def request_guard(request: Request, call_next):
    request_id = uuid.uuid4().hex
    path = request.url.path
    if path.endswith("/auth/login") or path.endswith("/auth/accept") or path.endswith("/chat/query") or path.endswith("/documents/upload"):
        limit = 10 if path.endswith("/auth/login") else 30
        client_ip = request.client.host if request.client else "unknown"
        key = f"rate:{path}:{client_ip}:{int(time.time() // 60)}"
        try:
            redis = Redis.from_url(settings.redis_url, socket_timeout=1)
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, 65)
            if count > limit:
                return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"X-Request-ID": request_id})
        except Exception:
            return JSONResponse({"detail": "Rate limit service unavailable"}, status_code=503, headers={"X-Request-ID": request_id})
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


for router in (health.router, auth.router, documents.router, search.router, chat.router, usage.router):
    app.include_router(router, prefix="/api/v1")
