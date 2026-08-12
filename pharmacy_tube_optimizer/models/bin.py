"""Physical tubing-bin model.

Each ``Bin`` represents a single physical destination bin and owns the list
of medication orders currently waiting in that bin.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pharmacy_tube_optimizer.models.medication_order import MedicationOrder


@dataclass
class Bin:
    """A physical tubing bin that holds pending medication orders."""

    bin_number: int | str
    unit: str | int | None = None
    room_prefix: int | str | None = None
    active: bool = True
    pending_medications: list[MedicationOrder] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Fill in default unit and room-prefix values from the bin number."""
        if self.unit is None:
            self.unit = self.bin_number
        if self.room_prefix is None:
            self.room_prefix = self.bin_number

    @property
    def bin_id(self) -> str:
        """Stable display identifier for the physical bin."""
        return f"BIN_{self.bin_number}"

    def add_medication(self, medication: MedicationOrder) -> None:
        """Place an order in this bin and synchronize its physical-bin field."""
        if medication not in self.pending_medications:
            self.pending_medications.append(medication)
        medication.assign_current_bin(self.bin_number)

    def remove_medication(self, order_id: str) -> None:
        """Remove the order with ``order_id`` from this bin, if present."""
        self.pending_medications = [m for m in self.pending_medications if m.order_id != order_id]

    def get_pending_medications(self) -> list[MedicationOrder]:
        """Return medications that have not already been sent or completed."""
        completed_statuses = {"TUBED", "COMPLETED", "DONE"}
        return [
            medication
            for medication in self.pending_medications
            if medication.active and not medication.tubed and medication.status.upper() not in completed_statuses
        ]

    def has_stat_medication(self) -> bool:
        """Return whether this bin has a pending STAT medication."""
        return any(m.is_stat() for m in self.get_pending_medications())
