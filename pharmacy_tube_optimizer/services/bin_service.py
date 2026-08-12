"""
bin_service.py

Handles the relationship between rooms and fixed tubing bins.

This service is responsible for:
    - finding the fixed bin associated with a room
    - retrieving bin information by bin id
    - returning the rooms associated with a bin
    - moving a medication from one bin to another after transfer detection
    - returning status information useful for a tubing board

This module does NOT decide:
    - whether a medication should be tubed
    - cutoff eligibility
    - medication priority
    - transfer detection logic
"""

from __future__ import annotations

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.models.patient_location import PatientLocation


class BinService:
    """Manage room-to-bin mapping and bin movement operations."""

    def __init__(self, bins: list[Bin] | None = None) -> None:
        self.bins = bins or []

    def find_bin_by_room(self, room: int) -> Bin | None:
        """Return the fixed bin associated with a room."""
        bin_number = PatientLocation.get_bin_number_from_room(room)
        for bin_obj in self.bins:
            if bin_obj.bin_number == bin_number:
                return bin_obj
        return None

    def get_bin_by_id(self, bin_number: int | str) -> Bin | None:
        """Return a bin object by its fixed bin number."""
        for bin_obj in self.bins:
            if bin_obj.bin_number == bin_number:
                return bin_obj
        return None

    def get_rooms_in_bin(self, bin_obj: Bin) -> list[int]:
        """Return the rooms that belong to a fixed bin."""
        if not isinstance(bin_obj.bin_number, int):
            return []
        return [room for room in range(bin_obj.bin_number * 1000, (bin_obj.bin_number + 1) * 1000)]

    def move_medication_to_bin(self, order: MedicationOrder, from_bin: Bin, to_bin: Bin) -> None:
        """Move a medication from one fixed bin to another."""
        from_bin.remove_medication(order.order_id)
        to_bin.add_medication(order)
        if order.location is not None:
            order.assign_current_bin(to_bin.bin_number)

    def get_bin_status(self, bin_obj: Bin) -> dict:
        """Return status information useful for a tubing board."""
        return {
            "bin_number": bin_obj.bin_number,
            "pending_count": len(bin_obj.get_pending_medications()),
            "has_stat": bin_obj.has_stat_medication(),
        }
