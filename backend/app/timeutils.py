"""Timezone-aware date/time helpers shared by the routers.

Centralized so "today" and display formatting are computed the same way
everywhere, in the configured local timezone rather than UTC.
"""

from __future__ import annotations
from typing import Optional

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import get_settings

_settings = get_settings()
_TZ = ZoneInfo(_settings.timezone)


def now_local() -> datetime:
    return datetime.now(_TZ)


def today_local() -> date:
    return now_local().date()


def default_shift(moment: Optional[datetime] = None) -> str:
    """Fallback only — the client normally sends its own shift choice
    explicitly (see index.html's defaultShiftForHour, which this mirrors).
    Day starts 8am, Night starts 8pm, but a scan shortly before a shift's
    start is treated as an early arrival for that shift rather than a
    leftover of the other one: before 8am defaults to day, and 6pm onward
    defaults to night.
    """
    hour = (moment or now_local()).astimezone(_TZ).hour
    if hour < 8:
        return "day"
    if hour >= 18:
        return "night"
    return "day"


def format_display_date(d: date) -> str:
    """e.g. '5 Aug 2026' — matches the Apps Script 'd MMM yyyy' format."""
    return d.strftime("%-d %b %Y")


def format_display_time(t: time) -> str:
    """e.g. '6:52 AM' — matches the Apps Script 'h:mm a' format."""
    return t.strftime("%-I:%M %p")
