"""Convenience factory for a complete, internally consistent mock dataset."""

from __future__ import annotations

from datetime import datetime

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
    """Generate saved random orders and populated numeric bins for engine tests."""
    orders = generate_random_medication_orders(count, seed=seed, reference_time=reference_time)
    bins = generate_bins(orders)
    database = InMemoryDatabase()
    database.save_orders(orders)
    database.save_bins(bins)
    return database, bins, orders
