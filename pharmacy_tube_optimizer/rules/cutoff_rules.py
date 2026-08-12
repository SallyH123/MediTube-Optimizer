"""
cutoff_rules.py

Handles only the cutoff/release decision for medication tubing.

This module answers:
    - Is the medication allowed to be released from a holding restriction?

It does NOT decide:
    - tubing-window eligibility
    - priority
    - bin assignment
    - transfer
"""

from datetime import datetime, time

from pharmacy_tube_optimizer.config import (
    DAY_CUTOFF_CURRENT_TIME,
    DAY_HOLD_DUE_TIME,
    NIGHT_CUTOFF_CURRENT_TIME,
    NIGHT_HOLD_DUE_TIME,
)

# Compatibility names retained for rule callers; values come from config.py.
NIGHT_MED_CUTOFF = NIGHT_HOLD_DUE_TIME
NIGHT_CURRENT_TIME_THRESHOLD = NIGHT_CUTOFF_CURRENT_TIME
DAY_MED_CUTOFF = DAY_HOLD_DUE_TIME
DAY_CURRENT_TIME_THRESHOLD = DAY_CUTOFF_CURRENT_TIME


def is_after_time(current_datetime: datetime, target_time: time) -> bool:
    """Return True when the current time is at or after the target time."""
    return current_datetime.time() >= target_time


def is_cutoff_released(current_datetime: datetime, due_datetime: datetime) -> bool:
    """Return True when a medication is released from cutoff restrictions."""
    current_time = current_datetime.time()
    due_time = due_datetime.time()

    if due_time >= NIGHT_MED_CUTOFF:
        return current_time >= NIGHT_CURRENT_TIME_THRESHOLD

    if due_time >= DAY_MED_CUTOFF:
        return current_time >= DAY_CURRENT_TIME_THRESHOLD

    return True
