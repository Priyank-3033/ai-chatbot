import logging
import time
from collections import defaultdict, deque

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.dependencies import lifespan, settings
from app.routes import admin_router, auth_router, chat_router, commerce_router, documents_router, products_router, realtime_router, system_router


app = FastAPI(title=settings.api_title, version="5.0.0", lifespan=lifespan)

logger = logging.getLogger("smartchat.api")
if not logger.handlers:
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 120
_request_buckets: dict[str, deque[float]] = defaultdict(deque)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.product_photos_path.mkdir(parents=True, exist_ok=True)
app.mount("/product-photos", StaticFiles(directory=settings.product_photos_path), name="product-photos")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info("%s %s -> %s (%.2fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.middleware("http")
async def rate_limit_requests(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _request_buckets[client_ip]
    while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please slow down and try again shortly."},
        )
    bucket.append(now)
    return await call_next(request)

app.include_router(system_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(commerce_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(realtime_router)

