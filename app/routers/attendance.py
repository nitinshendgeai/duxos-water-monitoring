"""Attendance module endpoints — staff, check-in, admin, config.

Kept fully isolated from the water module: separate tables, separate
router prefix, no shared queries. The admin PIN model matches the fix
already made to Code.gs this session: the raw PIN is never returned to
the client, and every mutating admin action requires it, checked here
server-side against app_config.
"""

from __future__ import annotations
from typing import Optional

import random
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.config import get_settings
from app.database import get_db
from app.errors import AppError
from app.schemas import (
    AdminActionIn,
    AttDataOut,
    AttendanceEventOut,
    CheckinIn,
    DeleteStaffIn,
    SaveConfigIn,
    StaffCreateIn,
    StaffOut,
    VerifyPinIn,
)
from app.timeutils import default_shift, now_local, today_local

router = APIRouter(prefix="/api/attendance", tags=["attendance"])
settings = get_settings()

DEFAULT_WINGS = {
    "A": {"name": "Wing A"},
    "B": {"name": "Wing B"},
    "C": {"name": "Wing C"},
    "OFFICE": {"name": "Office"},
    "GYM": {"name": "Gym"},
}


def _check_pin(db: Session, pin: str) -> None:
    configured = crud.get_config(db, "pin") or settings.default_admin_pin
    if not pin or pin != configured:
        raise AppError("Incorrect admin PIN.", status_code=403)


def _parse_date(value: Optional[str]) -> date_type:
    if not value:
        return today_local()
    return date_type.fromisoformat(value)


@router.get("/data", response_model=AttDataOut)
def get_attendance_data(
    date: Optional[str] = None, db: Session = Depends(get_db)
) -> AttDataOut:
    day = _parse_date(date)

    staff = [
        StaffOut(id=s.id, name=s.name, role=s.role, phone=s.phone, code=s.code)
        for s in crud.list_active_staff(db)
    ]
    events = [
        AttendanceEventOut(
            staffId=ev.staff_id,
            type=ev.event_type,
            wing=ev.location,
            time=ev.occurred_at.isoformat(),
            shift=ev.shift or "",
        )
        for ev in crud.get_attendance_for_date(db, day)
    ]
    wings = crud.get_wings(db) or DEFAULT_WINGS

    return AttDataOut(staff=staff, attendance=events, wings=wings)


@router.post("/verify-pin")
def verify_pin(payload: VerifyPinIn, db: Session = Depends(get_db)):
    configured = crud.get_config(db, "pin") or settings.default_admin_pin
    return {"ok": payload.pin == configured}


@router.post("/staff")
def add_staff(payload: StaffCreateIn, db: Session = Depends(get_db)):
    _check_pin(db, payload.pin)

    code = None
    for _ in range(50):
        candidate = str(random.randint(1000, 9999))
        if not crud.code_in_use(db, candidate):
            code = candidate
            break
    if code is None:
        raise AppError(
            "Could not generate a unique staff code, try again.", status_code=500
        )

    staff = crud.create_staff(
        db, name=payload.name, role=payload.role, phone=payload.phone, code=code
    )
    return {
        "ok": True,
        "staff": {
            "id": staff.id,
            "name": staff.name,
            "role": staff.role,
            "phone": staff.phone,
            "code": staff.code,
        },
    }


@router.post("/staff/delete")
def delete_staff(payload: DeleteStaffIn, db: Session = Depends(get_db)):
    _check_pin(db, payload.pin)
    crud.soft_delete_staff(db, payload.id)
    return {"ok": True}


@router.post("/checkin")
def checkin(payload: CheckinIn, db: Session = Depends(get_db)):
    staff = crud.get_staff_by_code(db, payload.code)
    if staff is None:
        raise AppError("Code not recognised", status_code=404)

    day = _parse_date(payload.date)
    last_event = crud.get_last_event_for_staff_on(db, staff.id, day)
    next_type = "out" if last_event and last_event.event_type == "in" else "in"

    moment = now_local()
    shift = payload.shift or default_shift(moment)
    event = crud.create_attendance_event(
        db,
        staff_id=staff.id,
        event_type=next_type,
        location=payload.location,
        shift=shift,
        event_date=day,
        occurred_at=moment,
    )

    return {
        "ok": True,
        "type": next_type,
        "time": event.occurred_at.isoformat(),
        "shift": shift,
        "staff": {
            "id": staff.id,
            "name": staff.name,
            "role": staff.role,
            "phone": staff.phone,
        },
    }


@router.post("/config")
def save_config(payload: SaveConfigIn, db: Session = Depends(get_db)):
    _check_pin(db, payload.pin)
    if payload.wings:
        for code, info in payload.wings.items():
            name = (info or {}).get("name") or code
            crud.upsert_wing(db, code, name)
    if payload.new_pin:
        crud.set_config(db, "pin", payload.new_pin)
    return {"ok": True}


@router.post("/clear")
def clear_all(payload: AdminActionIn, db: Session = Depends(get_db)):
    _check_pin(db, payload.pin)
    crud.clear_attendance_data(db)
    return {"ok": True}
