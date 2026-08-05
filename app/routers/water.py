"""Meter Reading / Tank Status / Dashboard endpoints.

Note on date/time: the original frontend only ever stamps the *current*
date/time into the "date"/"time" fields at form-open (they're read-only
display divs, never user-edited), and the original Apps Script backend
already treated its own server-generated "Created Timestamp" as the
authoritative value for all business logic (today's-activity checks),
not the client-sent date/time strings — that's exactly why those checks
used Created Timestamp instead. We keep that same authority split here:
the client still sends date/time (so the frontend payload-building code
doesn't need to change), but the stored reading_date/reading_time are
derived from the server clock at insert time, which avoids depending on
parsing a locale-formatted string (`Date.toLocaleDateString()` output
varies by device locale) for a value that was never truly authoritative.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import (
    DashboardOut,
    MeterReadingIn,
    MeterReadingOut,
    TankStatusIn,
    TodayActivities,
)
from app.timeutils import format_display_date, format_display_time, now_local

router = APIRouter(prefix="/api/water", tags=["water"])


@router.post("/meter")
def save_meter_reading(payload: MeterReadingIn, db: Session = Depends(get_db)):
    local_now = now_local()
    crud.create_meter_reading(
        db,
        reading_date=local_now.date(),
        reading_time=local_now.time(),
        recorded_by=payload.recorded_by,
        wing_a=payload.wing_a,
        wing_b=payload.wing_b,
        wing_c=payload.wing_c,
        remarks=payload.remarks or None,
    )
    return {"status": "success"}


@router.post("/tank")
def save_tank_status(payload: TankStatusIn, db: Session = Depends(get_db)):
    local_now = now_local()
    crud.create_tank_status(
        db,
        reading_date=local_now.date(),
        reading_time=local_now.time(),
        session=payload.session,
        ug_domestic_ab=payload.ug_domestic_ab,
        ug_domestic_c=payload.ug_domestic_c,
        ug_flushing_ab=payload.ug_flushing_ab,
        ug_flushing_c=payload.ug_flushing_c,
        fire_tank=payload.fire_tank,
        oh_dom_a=payload.oh_dom_a,
        oh_dom_b=payload.oh_dom_b,
        oh_dom_c=payload.oh_dom_c,
        oh_flush_a=payload.oh_flush_a,
        oh_flush_b=payload.oh_flush_b,
        oh_flush_c=payload.oh_flush_c,
        remarks=payload.remarks or None,
    )
    return {"status": "success"}


@router.get("/dashboard", response_model=DashboardOut)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    tank = crud.get_latest_tank_status(db)
    latest_tank = None
    if tank is not None:
        latest_tank = {
            "date": format_display_date(tank.reading_date),
            "time": format_display_time(tank.reading_time),
            "session": tank.session,
            "ugDomesticAB": float(tank.ug_domestic_ab),
            "ugDomesticC": float(tank.ug_domestic_c),
            "ugFlushingAB": float(tank.ug_flushing_ab),
            "ugFlushingC": float(tank.ug_flushing_c),
            "fireTank": float(tank.fire_tank),
            "ohDomA": float(tank.oh_dom_a),
            "ohDomB": float(tank.oh_dom_b),
            "ohDomC": float(tank.oh_dom_c),
            "ohFlushA": float(tank.oh_flush_a),
            "ohFlushB": float(tank.oh_flush_b),
            "ohFlushC": float(tank.oh_flush_c),
            "remarks": tank.remarks,
        }

    recent = crud.get_recent_meter_readings(db, 7)
    recent_out = [
        MeterReadingOut(
            date=format_display_date(r.reading_date),
            time=format_display_time(r.reading_time),
            recordedBy=r.recorded_by,
            wingA=float(r.wing_a),
            wingB=float(r.wing_b),
            wingC=float(r.wing_c),
            remarks=r.remarks,
        )
        for r in recent
    ]

    today = now_local().date()
    activities = TodayActivities(
        meterReadingDone=crud.has_meter_reading_on(db, today),
        morningTankDone=crud.has_tank_session_on(db, "Morning", today),
        afternoonTankDone=crud.has_tank_session_on(db, "Afternoon", today),
        nightTankDone=crud.has_tank_session_on(db, "Night", today),
    )

    return DashboardOut(
        latestTank=latest_tank,
        recentMeterReadings=recent_out,
        todayActivities=activities,
    )
