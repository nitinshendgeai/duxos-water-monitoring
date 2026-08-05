"""Thin repository/CRUD layer — one function per query, no business logic."""

from __future__ import annotations
from typing import Optional

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models


def create_meter_reading(db: Session, **fields) -> models.MeterReading:
    row = models.MeterReading(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_tank_status(db: Session, **fields) -> models.TankStatus:
    row = models.TankStatus(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_latest_tank_status(db: Session) -> Optional[models.TankStatus]:
    stmt = (
        select(models.TankStatus).order_by(models.TankStatus.created_at.desc()).limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_recent_meter_readings(db: Session, count: int = 7) -> list[models.MeterReading]:
    stmt = (
        select(models.MeterReading)
        .order_by(models.MeterReading.created_at.desc())
        .limit(count)
    )
    return list(db.execute(stmt).scalars())


def has_meter_reading_on(db: Session, day: date) -> bool:
    stmt = (
        select(models.MeterReading.id)
        .where(func.date(models.MeterReading.created_at) == day)
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def has_tank_session_on(db: Session, session_name: str, day: date) -> bool:
    stmt = (
        select(models.TankStatus.id)
        .where(models.TankStatus.session == session_name)
        .where(func.date(models.TankStatus.created_at) == day)
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def list_active_staff(db: Session) -> list[models.Staff]:
    stmt = (
        select(models.Staff)
        .where(models.Staff.deleted_at.is_(None))
        .order_by(models.Staff.name)
    )
    return list(db.execute(stmt).scalars())


def get_staff_by_code(db: Session, code: str) -> Optional[models.Staff]:
    stmt = select(models.Staff).where(
        models.Staff.code == code, models.Staff.deleted_at.is_(None)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_staff_by_id(db: Session, staff_id: str) -> Optional[models.Staff]:
    return db.get(models.Staff, staff_id)


def code_in_use(db: Session, code: str) -> bool:
    stmt = select(models.Staff.id).where(
        models.Staff.code == code, models.Staff.deleted_at.is_(None)
    )
    return db.execute(stmt).first() is not None


def create_staff(db: Session, **fields) -> models.Staff:
    row = models.Staff(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def soft_delete_staff(db: Session, staff_id: str) -> bool:
    row = db.get(models.Staff, staff_id)
    if not row or row.deleted_at is not None:
        return False
    row.deleted_at = datetime.utcnow()
    db.commit()
    return True


def get_attendance_for_date(db: Session, day: date) -> list[models.Attendance]:
    stmt = (
        select(models.Attendance)
        .where(models.Attendance.event_date == day)
        .order_by(models.Attendance.occurred_at)
    )
    return list(db.execute(stmt).scalars())


def get_last_event_for_staff_on(
    db: Session, staff_id: str, day: date
) -> Optional[models.Attendance]:
    stmt = (
        select(models.Attendance)
        .where(
            models.Attendance.staff_id == staff_id, models.Attendance.event_date == day
        )
        .order_by(models.Attendance.occurred_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def create_attendance_event(db: Session, **fields) -> models.Attendance:
    row = models.Attendance(**fields)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_wings(db: Session) -> dict[str, dict[str, str]]:
    stmt = select(models.Wing)
    return {w.code: {"name": w.name} for w in db.execute(stmt).scalars()}


def upsert_wing(db: Session, code: str, name: str) -> None:
    row = db.get(models.Wing, code)
    if row:
        row.name = name
    else:
        db.add(models.Wing(code=code, name=name))
    db.commit()


def get_config(db: Session, key: str) -> Optional[str]:
    row = db.get(models.AppConfig, key)
    return row.value if row else None


def set_config(db: Session, key: str, value: str) -> None:
    row = db.get(models.AppConfig, key)
    if row:
        row.value = value
    else:
        db.add(models.AppConfig(key=key, value=value))
    db.commit()


def clear_attendance_data(db: Session) -> None:
    db.query(models.Attendance).delete()
    db.query(models.Staff).delete()
    db.commit()
