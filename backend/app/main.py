import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.request_context import get_request_id, set_request_id
from app.core.runtime import initialize_runtime
from app.schemas.errors import ErrorResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_runtime()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    @application.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_request_id(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request failure",
                extra={"request_id": request_id, "path": request.url.path, "method": request.method},
            )
            raise

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        return response

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = get_request_id()
        payload = ErrorResponse(error="request_failed", detail=str(exc.detail), request_id=request_id)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = get_request_id()
        detail = "; ".join(
            [f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()]
        )
        payload = ErrorResponse(error="validation_failed", detail=detail, request_id=request_id)
        return JSONResponse(status_code=422, content=payload.model_dump())

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _: Exception):
        request_id = get_request_id()
        payload = ErrorResponse(
            error="internal_error",
            detail="The request could not be completed. Check backend logs for the request identifier.",
            request_id=request_id,
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    application.include_router(health_router, prefix="/api")
    application.include_router(documents_router, prefix="/api")
    application.include_router(chat_router, prefix="/api")
    return application


app = create_app()
