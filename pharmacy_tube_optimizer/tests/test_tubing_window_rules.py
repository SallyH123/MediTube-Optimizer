from datetime import datetime

from pharmacy_tube_optimizer.rules.tubing_window_rules import (
    get_tubing_window,
    get_hours_until_due,
    is_within_tubing_window,
)


def test_get_tubing_window_er_unit():
    assert get_tubing_window("ER")
    assert get_tubing_window("ER") == get_tubing_window("PERIOP")


def test_hours_until_due():
    current_time = datetime(2026, 8, 2, 14, 0)
    due_time = datetime(2026, 8, 2, 18, 0)
    assert get_hours_until_due(current_time, due_time) == 4.0


def test_within_tubing_window_normal_unit():
    current_time = datetime(2026, 8, 2, 14, 0)
    due_time = datetime(2026, 8, 2, 18, 0)
    assert is_within_tubing_window(current_time, due_time, "MICU") is True


def test_within_tubing_window_er_unit():
    current_time = datetime(2026, 8, 2, 14, 0)
    due_time = datetime(2026, 8, 2, 14, 45)
    assert is_within_tubing_window(current_time, due_time, "ER") is True
