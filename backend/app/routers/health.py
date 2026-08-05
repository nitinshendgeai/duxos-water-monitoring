from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])

APP_VERSION = "fastapi-v1"


@router.get("/health")
def health():
    return {
        "status": "ok",
        "message": "Water Monitoring backend is running.",
        "version": APP_VERSION,
    }


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # surfaced to caller, not swallowed
        return {"status": "error", "database": "unreachable", "detail": str(exc)}
    return {"status": "ok", "database": "connected"}
