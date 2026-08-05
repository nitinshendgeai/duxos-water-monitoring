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
    hour = (moment or now_local()).astimezone(_TZ).hour
    return "day" if 8 <= hour < 20 else "night"


def format_display_date(d: date) -> str:
    """e.g. '5 Aug 2026' — matches the Apps Script 'd MMM yyyy' format."""
    return d.strftime("%-d %b %Y")


def format_display_time(t: time) -> str:
    """e.g. '6:52 AM' — matches the Apps Script 'h:mm a' format."""
    return t.strftime("%-I:%M %p")
