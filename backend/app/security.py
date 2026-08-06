"""In-memory rate limiting for admin PIN attempts.

Global, not per-client-IP: Railway's edge proxy may not forward a
trustworthy client IP into request.client.host, and this app only ever
has one or two legitimate admins, so a single global lockout closes the
brute-force gap without depending on proxy header configuration. A
single Railway instance is assumed (no multi-process/multi-region
fan-out for this small app), so an in-memory counter is enough — no need
for a persistent table or Redis. State resets on redeploy/restart, which
is an acceptable trade-off for this app's size: worse case is a fresh
lockout window, not a security hole.
"""

from __future__ import annotations

import time

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900  # 15 minutes

_failure_timestamps: list[float] = []


def is_locked_out() -> bool:
    now = time.time()
    recent = [t for t in _failure_timestamps if now - t < LOCKOUT_SECONDS]
    _failure_timestamps[:] = recent
    return len(recent) >= MAX_ATTEMPTS


def record_failure() -> None:
    _failure_timestamps.append(time.time())


def record_success() -> None:
    _failure_timestamps.clear()
