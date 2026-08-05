"""SQLAlchemy 2.x ORM models.

Table/column choices mirror the original Google Sheets structure closely
(see Code.gs and the migrated Excel export) so the data migration is a
straight column-for-column copy with no semantic remapping, except:

- `staff` gains `deleted_at` (soft delete) so attendance history keeps a
  real foreign key and a real name/role lookup even after a staff member
  is "removed" — the Sheets version hard-deleted the row and fell back to
  showing "(removed staff)" in the log, which this improves on for free.
- `attendance.shift` is nullable because the live Google Sheet never
  actually had a Shift column (confirmed from the Excel export), even
  though the deployed frontend already sends one.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _staff_id() -> str:
    return f"s_{uuid.uuid4().hex}"


class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (
        CheckConstraint("wing_a >= 0", name="ck_meter_wing_a_nonneg"),
        CheckConstraint("wing_b >= 0", name="ck_meter_wing_b_nonneg"),
        CheckConstraint("wing_c >= 0", name="ck_meter_wing_c_nonneg"),
        UniqueConstraint("created_at", name="uq_meter_created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    reading_time: Mapped[time] = mapped_column(Time, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    wing_a: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    wing_b: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    wing_c: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TankStatus(Base):
    __tablename__ = "tank_status"
    __table_args__ = (
        CheckConstraint(
            "session IN ('Morning','Afternoon','Night')", name="ck_tank_session"
        ),
        CheckConstraint("ug_domestic_ab >= 0", name="ck_tank_ug_dom_ab_nonneg"),
        CheckConstraint("ug_domestic_c >= 0", name="ck_tank_ug_dom_c_nonneg"),
        CheckConstraint("ug_flushing_ab >= 0", name="ck_tank_ug_flush_ab_nonneg"),
        CheckConstraint("ug_flushing_c >= 0", name="ck_tank_ug_flush_c_nonneg"),
        CheckConstraint("fire_tank BETWEEN 0 AND 100", name="ck_tank_fire_pct"),
        CheckConstraint("oh_dom_a BETWEEN 0 AND 100", name="ck_tank_oh_dom_a_pct"),
        CheckConstraint("oh_dom_b BETWEEN 0 AND 100", name="ck_tank_oh_dom_b_pct"),
        CheckConstraint("oh_dom_c BETWEEN 0 AND 100", name="ck_tank_oh_dom_c_pct"),
        CheckConstraint("oh_flush_a BETWEEN 0 AND 100", name="ck_tank_oh_flush_a_pct"),
        CheckConstraint("oh_flush_b BETWEEN 0 AND 100", name="ck_tank_oh_flush_b_pct"),
        CheckConstraint("oh_flush_c BETWEEN 0 AND 100", name="ck_tank_oh_flush_c_pct"),
        UniqueConstraint("created_at", name="uq_tank_created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    reading_time: Mapped[time] = mapped_column(Time, nullable=False)
    session: Mapped[str] = mapped_column(String(20), nullable=False)
    ug_domestic_ab: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    ug_domestic_c: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    ug_flushing_ab: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    ug_flushing_c: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    fire_tank: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_dom_a: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_dom_b: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_dom_c: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_flush_a: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_flush_b: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    oh_flush_c: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Staff(Base):
    __tablename__ = "staff"
    __table_args__ = (
        CheckConstraint(
            "role IN ('security','technical','manager','gym_attendant')",
            name="ck_staff_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_staff_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    attendance_events: Mapped[list["Attendance"]] = relationship(back_populates="staff")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("event_type IN ('in','out')", name="ck_attendance_event_type"),
        CheckConstraint(
            "shift IN ('day','night') OR shift IS NULL", name="ck_attendance_shift"
        ),
        UniqueConstraint("staff_id", "occurred_at", name="uq_attendance_staff_time"),
        Index("ix_attendance_event_date", "event_date"),
        Index("ix_attendance_staff_event_date", "staff_id", "event_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("staff.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)
    location: Mapped[str] = mapped_column(String(20), nullable=False)
    shift: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    staff: Mapped[Staff] = relationship(back_populates="attendance_events")


class Wing(Base):
    """Named check-in locations (3 residential wings + Office + Gym)."""

    __tablename__ = "wings"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AppConfig(Base):
    """Single key/value settings table — currently just the admin PIN."""

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
