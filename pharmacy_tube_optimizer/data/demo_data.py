"""Deterministic medication scenarios for the 20:00 tubing-board demo."""

from __future__ import annotations

from datetime import datetime, timedelta

from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder


DEMO_CURRENT_TIME = datetime(2026, 9, 8, 20, 0)


def create_demo_dataset() -> tuple[list[Bin], list[MedicationOrder]]:
    """Return the ten fixed orders used by the interactive cutoff demo."""
    today = DEMO_CURRENT_TIME.date()
    tomorrow = today + timedelta(days=1)
    orders = [
        MedicationOrder("DEMO-001", "Norepinephrine", "IV", datetime.combine(today, datetime.min.time()).replace(hour=20, minute=30), "STAT", 7015, "7", current_bin=7),
        MedicationOrder("DEMO-002", "Vancomycin", "IV", datetime.combine(today, datetime.min.time()).replace(hour=22), "Routine", 2015, "SICU", current_bin="SICU"),
        MedicationOrder("DEMO-003", "Piperacillin-tazobactam", "IV", datetime.combine(tomorrow, datetime.min.time()).replace(hour=2), "Routine", 4015, "4", current_bin=4),
        MedicationOrder("DEMO-004", "Acetaminophen", "PO", datetime.combine(today, datetime.min.time()).replace(hour=23), "Routine", 2016, "SICU", current_bin="SICU"),
        MedicationOrder("DEMO-005", "Furosemide", "IV", datetime.combine(today, datetime.min.time()).replace(hour=19, minute=50), "Routine", 5014, "5", current_bin=5),
        MedicationOrder("DEMO-006", "Ceftriaxone", "IV", datetime.combine(today, datetime.min.time()).replace(hour=21, minute=30), "Routine", 8014, "ED", current_bin="ED"),
        MedicationOrder("DEMO-007", "Cefepime", "IV", datetime.combine(today, datetime.min.time()).replace(hour=21, minute=30), "Routine", 8015, "ED", current_bin="ED"),
        MedicationOrder("DEMO-008", "Insulin", "SUBQ", datetime.combine(today, datetime.min.time()).replace(hour=21), "Routine", 6015, "6", current_bin=6),
        MedicationOrder("DEMO-009", "Hydrocortisone cream", "TOPICAL", datetime.combine(today, datetime.min.time()).replace(hour=23), "Routine", 2017, "SICU", current_bin="SICU"),
        MedicationOrder("DEMO-010", "Unknown-location medication", "IV", datetime.combine(today, datetime.min.time()).replace(hour=21, minute=30), "Routine", None, None, current_bin="UNKNOWN"),
    ]
    # Preserve the original ED location while placing Cefepime in its current
    # patient room and destination unit for transfer reconciliation.
    orders[6].update_location(room=5015, unit="5")
    bins = [Bin(bin_number) for bin_number in TUBING_BIN_LOCATIONS]
    bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}
    for order in orders:
        bins_by_number[order.current_bin].add_medication(order)
    return bins, orders
