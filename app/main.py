"""FastAPI Application entrypoint with middleware, error formatting, and routing."""

import truststore

truststore.inject_into_ssl()
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import settings
from app.core.logging import correlation_id_ctx, logger
from app.schemas.errors import ErrorDetail, ErrorResponse
from app.substrate.gateway import close_live_mcp, initialize_live_mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    banner = settings.startup_banner()
    print(banner)
    logger.info("Application starting up with active runtime modes:")
    for k, v in settings.runtime_modes.items():
        logger.info(f"  {k}: {v}")
    await initialize_live_mcp()
    try:
        yield
    finally:
        await close_live_mcp()
        logger.info("Application shutting down.")


app = FastAPI(
    title="AI-Powered Supply Chain Disruption & Recovery Assistant",
    description="Multi-agent decision intelligence system combining Synapt Substrate with ML and LiteLLM.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (localhost allowed by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8501",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_correlation_id_middleware(request: Request, call_next):
    """Assigns or propagates request correlation ID for end-to-end tracing."""
    corr_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    token = correlation_id_ctx.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
    finally:
        correlation_id_ctx.reset(token)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Formats HTTP exceptions to the standard ErrorResponse schema."""
    code = "INTERNAL"
    message = str(exc.detail)
    details = None

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "VALIDATION_ERROR" if exc.status_code == 422 else "INTERNAL")
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details")

    err_payload = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=exc.status_code, content=err_payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic request validation errors to standard ErrorResponse schema."""
    err_payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request body or query parameter failed schema validation.",
            details=exc.errors(),
        )
    )
    return JSONResponse(status_code=422, content=err_payload.model_dump())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Fallback handler catching unhandled server exceptions."""
    logger.exception(f"Unhandled server error: {exc}")
    err_payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL",
            message="Internal server error encountered processing request.",
            details=str(exc),
        )
    )
    return JSONResponse(status_code=500, content=err_payload.model_dump())


# Mount API routes
app.include_router(router)
