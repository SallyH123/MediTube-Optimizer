"""
medication_service.py

Provides medication-order data access and status management.

This service is responsible for:
    - finding medication orders by order number
    - returning medications associated with a specific bin
    - returning pending medications that have not yet been tubed or completed
    - reading medication route and due time information
    - updating medication status after an action

This module does NOT decide:
    - priority
    - cutoff restrictions
    - tubing-window eligibility
    - transfer destination
"""

from __future__ import annotations

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.rules.priority_rules import calculate_bin_priority_score
from pharmacy_tube_optimizer.utils.logger import Logger


class MedicationService:
    """Provide medication-order data access and status management."""

    def __init__(self, orders: list[MedicationOrder] | None = None, logger: Logger | None = None) -> None:
        self.orders = orders or []
        self.logger = logger or Logger()

    def get_medication_by_order_number(self, order_number: str) -> MedicationOrder | None:
        """Return a medication order by its real-world order number."""
        for order in self.orders:
            if order.order_id == order_number:
                return order
        return None

    def get_medications_for_bin(self, bin_obj: Bin) -> list[MedicationOrder]:
        """Return all medication orders currently associated with a bin."""
        return [order for order in self.orders if order.current_bin == bin_obj.bin_number]

    def get_pending_medications(self) -> list[MedicationOrder]:
        """Return medication orders that are not already tubed or completed."""
        return [order for order in self.orders if order.status.upper() not in {"TUBED", "COMPLETED", "DONE"}]

    def get_medication_route(self, order: MedicationOrder) -> str:
        """Return the medication route such as IV, PO, or SubQ."""
        return order.route.upper()

    def get_medication_due_time(self, order: MedicationOrder) -> str | None:
        """Return the scheduled administration time for a medication order."""
        if order.due_time is None:
            return None
        return order.due_time.isoformat()

    def update_medication_status(self, order: MedicationOrder, status: str) -> MedicationOrder:
        """Update the status of a medication after an action."""
        order.update_status(status)
        return order

    def tube_medication(self, order: MedicationOrder, bin_obj: Bin) -> MedicationOrder:
        """Mark an order as tubed, remove it from the bin, and record the action."""
        if order not in bin_obj.get_pending_medications():
            raise ValueError(f"Order {order.order_id} is not pending in Bin {bin_obj.bin_number}")

        order.mark_tubed()
        bin_obj.remove_medication(order.order_id)
        self.logger.log_medication_tubed(order.medication, bin_obj.bin_number)
        return order

    def calculate_bin_priority(self, bin_obj: Bin) -> float:
        """Return the priority-rule score for a bin's pending medications."""
        medications = [
            {"status": order.status, "route": order.route}
            for order in bin_obj.get_pending_medications()
        ]
        return calculate_bin_priority_score(medications)
