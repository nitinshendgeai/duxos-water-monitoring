import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import AppError
from app.routers import attendance, health, water

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("duxos_water")

settings = get_settings()

app = FastAPI(
    title="DuxOS Water Monitoring API",
    description="Meter Reading, Tank Status, Dashboard and Attendance backend (replaces the Google Apps Script deployment).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(water.router)
app.include_router(attendance.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    # "error" is kept alongside "message" for backward compatibility: the
    # original Attendance frontend reads res.error specifically (e.g. the
    # "Code not recognised" check-in failure), while the Water Monitoring
    # side reads res.message — both are populated so neither call site
    # needed to change.
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "ok": False,
            "message": exc.message,
            "error": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    message = first.get("msg", "Invalid request.")
    return JSONResponse(
        status_code=422,
        content={"status": "error", "ok": False, "message": message, "error": message},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    message = "Internal server error."
    return JSONResponse(
        status_code=500,
        content={"status": "error", "ok": False, "message": message, "error": message},
    )
