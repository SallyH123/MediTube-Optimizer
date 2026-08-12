"""
tubing_window_rules.py

Determines whether a medication is within the appropriate tubing time window.

Rules:
    Normal units:
        within 5 hours of due time

    ER / Periop:
        within 1 hour of due time

This module does NOT decide:
    - priority
    - cutoff restrictions
    - bin assignment
    - transfer
"""

from datetime import datetime, timedelta
from typing import Protocol

from pharmacy_tube_optimizer.config import (
    BIN_REVIEW_WINDOW_HOURS,
    ER_ROUTINE_WINDOW_HOURS,
    ER_UNITS,
    STANDARD_ROUTINE_WINDOW_HOURS,
)

STANDARD_TUBE_WINDOW = timedelta(hours=STANDARD_ROUTINE_WINDOW_HOURS)
ER_PERIOP_TUBE_WINDOW = timedelta(hours=ER_ROUTINE_WINDOW_HOURS)
BIN_CLOSEST_MEDICATION_WINDOW = timedelta(hours=BIN_REVIEW_WINDOW_HOURS)


class HasDueTime(Protocol):
    """Minimum medication interface needed for bin-level timing checks."""

    due_time: datetime | None


def normalize_unit(unit: str) -> str:
    """Normalize unit names to a standard uppercase format."""
    return (unit or "").upper()


def is_special_window_unit(unit: str) -> bool:
    """Return True when the unit uses the 1-hour tubing window."""
    return normalize_unit(unit) in ER_UNITS


def get_tubing_window(unit: str) -> timedelta:
    """Return the tubing window based on the unit type."""
    if is_special_window_unit(unit):
        return ER_PERIOP_TUBE_WINDOW
    return STANDARD_TUBE_WINDOW


def get_hours_until_due(current_time: datetime, due_time: datetime) -> float:
    """Return the number of hours remaining until the medication is due."""
    difference = due_time - current_time
    return difference.total_seconds() / 3600


def is_within_tubing_window(current_time: datetime, due_time: datetime, unit: str) -> bool:
    """Return True when the medication is within the allowed tubing window."""
    window = get_tubing_window(unit)
    time_until_due = due_time - current_time
    return time_until_due <= window


def get_closest_medication_due_time(
    medications: list[HasDueTime], current_time: datetime
) -> datetime | None:
    """Return a bin's earliest scheduled due time.

    Overdue medications are updated to ``current_time`` before the comparison,
    so an overdue dose makes its bin immediately eligible for bin-level review.
    Orders without a due time do not determine when a bin is reviewed.
    """
    due_orders = [order for order in medications if order.due_time is not None]
    if not due_orders:
        return None

    for order in due_orders:
        if order.due_time < current_time:
            order.due_time = current_time

    return min(order.due_time for order in due_orders)


def is_closest_medication_within_tubing_window(
    medications: list[HasDueTime], current_time: datetime
) -> bool:
    """Return whether the bin's closest medication is due within one hour."""
    closest_due_time = get_closest_medication_due_time(medications, current_time)
    return closest_due_time is not None and closest_due_time - current_time <= BIN_CLOSEST_MEDICATION_WINDOW
