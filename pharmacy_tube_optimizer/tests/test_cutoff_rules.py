from datetime import datetime, time

from pharmacy_tube_optimizer.rules.cutoff_rules import is_cutoff_released


def test_night_cutoff_blocked_before_release():
    current_time = datetime(2026, 8, 2, 20, 0)
    due_time = datetime(2026, 8, 2, 21, 0)
    assert is_cutoff_released(current_time, due_time) is False


def test_day_cutoff_blocked_before_release():
    current_time = datetime(2026, 8, 2, 8, 0)
    due_time = datetime(2026, 8, 2, 9, 0)
    assert is_cutoff_released(current_time, due_time) is False


def test_regular_time_released():
    current_time = datetime(2026, 8, 2, 10, 0)
    due_time = datetime(2026, 8, 2, 9, 0)
    assert is_cutoff_released(current_time, due_time) is True
