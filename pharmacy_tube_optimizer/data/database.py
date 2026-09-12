from __future__ import annotations

"""In-memory persistence used by generated data and local demonstrations."""

from collections.abc import Iterable

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder


class InMemoryDatabase:
    def __init__(self) -> None:
        """Create empty order and bin stores keyed by their identifiers."""
        self.orders: dict[str, MedicationOrder] = {}
        self.bins: dict[int | str, Bin] = {}

    def save_order(self, order: MedicationOrder) -> None:
        """Store or replace one medication order."""
        self.orders[order.order_id] = order

    def save_orders(self, orders: Iterable[MedicationOrder]) -> None:
        """Store a collection of medication orders by order ID."""
        for order in orders:
            self.save_order(order)

    def get_order(self, order_id: str) -> MedicationOrder | None:
        """Return one order, if it has been saved."""
        return self.orders.get(order_id)

    def save_bin(self, bin_obj: Bin) -> None:
        """Store a tubing bin by its fixed bin number."""
        self.bins[bin_obj.bin_number] = bin_obj

    def save_bins(self, bins: Iterable[Bin]) -> None:
        """Store a collection of tubing bins."""
        for bin_obj in bins:
            self.save_bin(bin_obj)

    def get_bins(self) -> list[Bin]:
        """Return saved bins in a deterministic display order."""
        return [self.bins[number] for number in sorted(self.bins, key=str)]

    def get_pending_orders(self) -> list[MedicationOrder]:
        """Return active orders that have not yet been tubed."""
        completed_statuses = {"TUBED", "COMPLETED", "DONE"}
        return [order for order in self.orders.values() if order.status.upper() not in completed_statuses]

    def update_order_status(self, order_id: str, status: str) -> MedicationOrder | None:
        """Update and return an order when it exists, otherwise return ``None``."""
        order = self.orders.get(order_id)
        if order is not None:
            order.update_status(status)
        return order
