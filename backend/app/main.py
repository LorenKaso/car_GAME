from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import auth, catalog, health, players
from app.core.body_limit import BodyLimitMiddleware
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.rate_limit import RateLimiter
from app.db.session import Database


def create_app(settings=None):
    settings = settings or get_settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        database.close()

    app = FastAPI(
        title="Racing Platform API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.limiter = RateLimiter(database, settings.rate_limit_key.get_secret_value())
    app.add_middleware(BodyLimitMiddleware)

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else {}
        if exc.status == 429:
            headers["Retry-After"] = "60"
        return JSONResponse({"error": exc.code}, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Never return Pydantic's raw input or context: they may contain passwords/tokens.
        return JSONResponse(
            {
                "error": "invalid_request",
                "fields": [{"path": list(e["loc"]), "type": e["type"]} for e in exc.errors()],
            },
            status_code=422,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        # SQL text/parameters/connection strings are not returned or logged.
        return JSONResponse({"error": "database_unavailable"}, status_code=503)

    for router in (health.router, auth.router, players.router, catalog.router):
        app.include_router(router)
    return app


app = create_app()
