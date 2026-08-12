from __future__ import annotations

from datetime import datetime


def get_current_time() -> datetime:
    return datetime.now()


def is_before_cutoff(current_time: datetime, cutoff: str) -> bool:
    cutoff_minutes = _to_minutes(cutoff)
    current_minutes = current_time.hour * 60 + current_time.minute
    return current_minutes < cutoff_minutes


def calculate_hours_difference(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 3600, 2)


def _to_minutes(value: str) -> int:
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute
