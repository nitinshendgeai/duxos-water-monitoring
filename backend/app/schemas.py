"""Pydantic request/response schemas.

Field names/aliases intentionally mirror the exact JSON keys the existing
frontend already sends and expects (camelCase, e.g. "wingA", "ugDomesticAB")
so index.html's request-building code doesn't need to change — only the
URL it calls does.
"""

from __future__ import annotations
from typing import Optional

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

CAMEL_CONFIG = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Meter Reading
# ---------------------------------------------------------------------------
class MeterReadingIn(BaseModel):
    model_config = CAMEL_CONFIG

    date: str
    time: str
    recorded_by: str = Field(alias="recordedBy")
    wing_a: float = Field(alias="wingA")
    wing_b: float = Field(alias="wingB")
    wing_c: float = Field(alias="wingC")
    remarks: Optional[str] = None

    @field_validator("wing_a", "wing_b", "wing_c")
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Meter readings cannot be negative.")
        return v


class MeterReadingOut(BaseModel):
    model_config = CAMEL_CONFIG

    date: str
    time: str
    recorded_by: str = Field(alias="recordedBy")
    wing_a: float = Field(alias="wingA")
    wing_b: float = Field(alias="wingB")
    wing_c: float = Field(alias="wingC")
    remarks: Optional[str] = None


# ---------------------------------------------------------------------------
# Tank Status
# ---------------------------------------------------------------------------
class TankStatusIn(BaseModel):
    model_config = CAMEL_CONFIG

    date: str
    time: str
    session: str
    ug_domestic_ab: float = Field(alias="ugDomesticAB")
    ug_domestic_c: float = Field(alias="ugDomesticC")
    ug_flushing_ab: float = Field(alias="ugFlushingAB")
    ug_flushing_c: float = Field(alias="ugFlushingC")
    fire_tank: float = Field(alias="fireTank")
    oh_dom_a: float = Field(alias="ohDomA")
    oh_dom_b: float = Field(alias="ohDomB")
    oh_dom_c: float = Field(alias="ohDomC")
    oh_flush_a: float = Field(alias="ohFlushA")
    oh_flush_b: float = Field(alias="ohFlushB")
    oh_flush_c: float = Field(alias="ohFlushC")
    remarks: Optional[str] = None

    @field_validator("session")
    @classmethod
    def valid_session(cls, v: str) -> str:
        if v not in ("Morning", "Afternoon", "Night"):
            raise ValueError("Session must be Morning, Afternoon, or Night.")
        return v

    @field_validator(
        "ug_domestic_ab", "ug_domestic_c", "ug_flushing_ab", "ug_flushing_c"
    )
    @classmethod
    def non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Tank litre readings cannot be negative.")
        return v

    @field_validator(
        "fire_tank",
        "oh_dom_a",
        "oh_dom_b",
        "oh_dom_c",
        "oh_flush_a",
        "oh_flush_b",
        "oh_flush_c",
    )
    @classmethod
    def percent_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("Percentage fields must be between 0 and 100.")
        return v


class TodayActivities(BaseModel):
    model_config = CAMEL_CONFIG

    meter_reading_done: bool = Field(alias="meterReadingDone")
    morning_tank_done: bool = Field(alias="morningTankDone")
    afternoon_tank_done: bool = Field(alias="afternoonTankDone")
    night_tank_done: bool = Field(alias="nightTankDone")


class LatestTankOut(BaseModel):
    model_config = CAMEL_CONFIG

    date: str
    time: str
    session: str
    ug_domestic_ab: float = Field(alias="ugDomesticAB")
    ug_domestic_c: float = Field(alias="ugDomesticC")
    ug_flushing_ab: float = Field(alias="ugFlushingAB")
    ug_flushing_c: float = Field(alias="ugFlushingC")
    fire_tank: float = Field(alias="fireTank")
    oh_dom_a: float = Field(alias="ohDomA")
    oh_dom_b: float = Field(alias="ohDomB")
    oh_dom_c: float = Field(alias="ohDomC")
    oh_flush_a: float = Field(alias="ohFlushA")
    oh_flush_b: float = Field(alias="ohFlushB")
    oh_flush_c: float = Field(alias="ohFlushC")
    remarks: Optional[str] = None


class DashboardOut(BaseModel):
    model_config = CAMEL_CONFIG

    status: str = "success"
    latest_tank: Optional[LatestTankOut] = Field(default=None, alias="latestTank")
    recent_meter_readings: list[MeterReadingOut] = Field(
        default_factory=list, alias="recentMeterReadings"
    )
    today_activities: TodayActivities = Field(alias="todayActivities")


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
class StaffOut(BaseModel):
    id: str
    name: str
    role: str
    phone: Optional[str] = None
    code: str


class StaffCreateIn(BaseModel):
    name: str
    role: str
    phone: Optional[str] = None
    pin: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in (
            "security",
            "technical",
            "manager",
            "gym_attendant",
            "security_supervisor",
            "housekeeping_supervisor",
            "housekeeping",
        ):
            raise ValueError("Unknown role.")
        return v

    @field_validator("name")
    @classmethod
    def name_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name is required.")
        return v.strip()


class AttendanceEventOut(BaseModel):
    staff_id: str = Field(alias="staffId")
    type: str
    wing: str
    time: str
    shift: str = ""

    model_config = CAMEL_CONFIG


class WingsMap(BaseModel):
    """Free-form {code: {name}} map, matching the original JSON blob shape."""

    model_config = ConfigDict(extra="allow")


class AttDataOut(BaseModel):
    ok: bool = True
    staff: list[StaffOut]
    attendance: list[AttendanceEventOut]
    wings: dict[str, dict[str, str]]


class CheckinIn(BaseModel):
    code: str
    location: str
    date: Optional[str] = None
    shift: Optional[str] = None


class VerifyPinIn(BaseModel):
    pin: str


class SaveConfigIn(BaseModel):
    pin: str
    wings: Optional[dict[str, dict[str, str]]] = None
    new_pin: Optional[str] = Field(default=None, alias="newPin")

    model_config = CAMEL_CONFIG


class AdminActionIn(BaseModel):
    pin: str


class DeleteStaffIn(BaseModel):
    id: str
    pin: str
