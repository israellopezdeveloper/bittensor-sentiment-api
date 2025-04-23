from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.types import ExceptionHandler

from app.api.v1 import tao_dividends, wallets
from app.cache.singleton import redis_cache
from app.db.session import init_db

"""
Application entry point. Defines the FastAPI app, routes, and lifecycle events.
"""


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={'detail': 'Rate limit exceeded'},
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    print('Startup...', flush=True)
    try:
        await redis_cache.connect()
    except Exception as e:
        print(f'Redis connection error: {e}', flush=True)

    try:
        await init_db()
    except Exception as e:
        print(f'Database initialization error: {e}', flush=True)

    print('Startup done.', flush=True)
    yield

    print('Shutting down...', flush=True)
    try:
        await redis_cache.close()
    except Exception as e:
        print(f'Redis shutdown error: {e}', flush=True)


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title='Bittensor Sentiment API',
    version='1.0.0',
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(ExceptionHandler, rate_limit_exceeded_handler))


app.include_router(tao_dividends.router, prefix='/api/v1', tags=['tao_dividends'])
app.include_router(wallets.router, prefix='/api/v1', tags=['wallets'])


@app.get('/health')
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: A JSON object with a 'status' key.
    """
    return {'status': 'ok'}


@app.get('/openapi.json', include_in_schema=False)
async def get_openapi():
    from fastapi.openapi.utils import get_openapi

    return get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
