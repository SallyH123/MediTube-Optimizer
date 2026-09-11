"""Convenience factory for a complete, internally consistent mock dataset."""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random

from pharmacy_tube_optimizer.data.database import InMemoryDatabase
from pharmacy_tube_optimizer.data.medication_data import (
    generate_bins,
    generate_medication_orders,
    generate_random_medication_orders,
    place_orders_in_bins,
)
from pharmacy_tube_optimizer.data.transfer_data import (
    generate_patient_location_data,
    generate_patient_transfers,
    generate_random_patient_transfer,
)
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder

__all__ = [
    "generate_bins",
    "generate_medication_orders",
    "generate_mock_dataset",
    "generate_random_medication_orders",
    "place_orders_in_bins",
    "generate_random_mock_dataset",
    "generate_patient_location_data",
    "generate_patient_transfers",
    "generate_random_patient_transfer",
]


def generate_mock_dataset() -> tuple[InMemoryDatabase, list[Bin], list[MedicationOrder]]:
    """Generate and save mock data ready for services and tubing-rule evaluation."""
    orders = generate_medication_orders()
    bins = generate_bins(orders)
    database = InMemoryDatabase()
    database.save_orders(orders)
    database.save_bins(bins)
    return database, bins, orders


def generate_random_mock_dataset(
    count: int = 10, *, seed: int | None = None, reference_time: datetime | None = None
) -> tuple[InMemoryDatabase, list[Bin], list[MedicationOrder]]:
    """Generate a random board with one transfer for the live workflow demo."""
    orders = generate_random_medication_orders(count, seed=seed, reference_time=reference_time)
    bins = generate_bins(orders)
    # Keep one medication in its original physical bin while updating the
    # patient location. Its due time is within the review window so the
    # engine checks, detects, and reports this transfer on the first board
    # request instead of leaving the alert dependent on random scheduling.
    if orders:
        transferred_order, _, _ = generate_random_patient_transfer(orders, rng=Random(seed))
        transferred_order.due_time = (reference_time or datetime.now()) + timedelta(minutes=30)
    database = InMemoryDatabase()
    database.save_orders(orders)
    database.save_bins(bins)
    return database, bins, orders
