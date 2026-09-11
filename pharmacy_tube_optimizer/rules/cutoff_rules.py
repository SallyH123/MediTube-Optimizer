"""
cutoff_rules.py

Determines when medication orders are released for tubing.

Night-batch orders due from 21:00 through 08:59 release at 20:30 on
the preceding evening. Day-batch orders due from 09:00 through 20:59
release at 08:30 on their due date.

This module answers:
    - Is the medication allowed to be released from a holding restriction?

It does NOT decide:
    - tubing-window eligibility
    - priority
    - bin assignment
    - transfer
"""

from datetime import datetime, time, timedelta

from pharmacy_tube_optimizer.config import (
    DAY_CUTOFF_CURRENT_TIME,
    DAY_HOLD_DUE_TIME,
    NIGHT_CUTOFF_CURRENT_TIME,
    NIGHT_HOLD_DUE_TIME,
)

# Named cutoff values sourced from the shared configuration.
NIGHT_MED_CUTOFF = NIGHT_HOLD_DUE_TIME
NIGHT_CURRENT_TIME_THRESHOLD = NIGHT_CUTOFF_CURRENT_TIME
DAY_MED_CUTOFF = DAY_HOLD_DUE_TIME
DAY_CURRENT_TIME_THRESHOLD = DAY_CUTOFF_CURRENT_TIME


def is_after_time(current_datetime: datetime, target_time: time) -> bool:
    """Return whether a time of day is at or after the supplied threshold."""
    return current_datetime.time() >= target_time


def is_cutoff_released(current_datetime: datetime, due_datetime: datetime) -> bool:
    """Return whether the order's day or overnight batch has been released."""
    due_time = due_datetime.time()

    if due_time >= NIGHT_MED_CUTOFF:
        release_datetime = datetime.combine(due_datetime.date(), NIGHT_CURRENT_TIME_THRESHOLD)
    elif due_time < DAY_MED_CUTOFF:
        release_datetime = datetime.combine(
            due_datetime.date() - timedelta(days=1), NIGHT_CURRENT_TIME_THRESHOLD
        )
    else:
        release_datetime = datetime.combine(due_datetime.date(), DAY_CURRENT_TIME_THRESHOLD)

    return current_datetime >= release_datetime
