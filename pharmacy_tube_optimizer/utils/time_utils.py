from __future__ import annotations

"""Small time-conversion helpers shared by command-line utilities."""

from datetime import datetime


def get_current_time() -> datetime:
    """Return the current local timestamp."""
    return datetime.now()


def is_before_cutoff(current_time: datetime, cutoff: str) -> bool:
    """Return whether a timestamp occurs before an HH:MM cutoff."""
    cutoff_minutes = _to_minutes(cutoff)
    current_minutes = current_time.hour * 60 + current_time.minute
    return current_minutes < cutoff_minutes


def calculate_hours_difference(start: datetime, end: datetime) -> float:
    """Return the elapsed duration between two timestamps in hours."""
    return round((end - start).total_seconds() / 3600, 2)


def _to_minutes(value: str) -> int:
    """Convert an HH:MM string to minutes after midnight."""
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute
