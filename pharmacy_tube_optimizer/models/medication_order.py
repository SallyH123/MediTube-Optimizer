"""
medication_order.py

Domain model representing a medication order.

Responsibilities:
    - store medication order attributes (id, route, due time, status, location)
    - provide simple helpers used by rules and services (time-until-due, type checks,
      location updates, and a serializable order summary)

This model does NOT:
    - implement business rules such as cutoff or tubing-window logic
    - access external data sources
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pharmacy_tube_optimizer.models.patient_location import PatientLocation
from pharmacy_tube_optimizer.utils.validators import validate_medication_order


@dataclass
class MedicationOrder:
    """A single medication administration order.

    Fields mirror the real-world order record and include optional patient
    location information. Services and rules read these attributes when
    making tubing decisions.
    """

    order_id: str
    medication: str
    route: str
    due_time: Optional[datetime] = None
    status: str = "Routine"
    room: Optional[int] = None
    unit: Optional[str] = None
    location: Optional[PatientLocation] = None
    previous_location: Optional[PatientLocation] = None
    patient_id: str = ""
    current_bin: int | str | None = None
    tubed: bool = False
    active: bool = True
    pre_tubing_status: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate the incoming order and ensure a `location` exists when possible.

        If only a room number is supplied we create a `PatientLocation` so
        other code can rely on `order.location.bin_number` and `order.location.unit`.
        """
        validate_medication_order(self)
        if self.location is None and self.room is not None:
            self.location = PatientLocation(
                room=self.room,
                unit=self.unit or "",
                bin_number=PatientLocation.get_bin_number_from_room(self.room),
            )
        if self.current_bin is None and self.location is not None:
            self.current_bin = self.location.get_bin_number()
        if self.status.upper() == "TUBED":
            self.tubed = True

    @property
    def order_number(self) -> str:
        """Business-friendly alias for the unique medication order ID."""
        return self.order_id

    @property
    def medication_name(self) -> str:
        """Business-friendly alias for the medication name."""
        return self.medication

    def calculate_time_until_due(self, current_time: Optional[datetime] = None) -> Optional[int]:
        """Return whole minutes until the scheduled administration time.

        Returns `None` when no `due_time` is set. When `current_time` is
        omitted `datetime.now()` is used as the reference.
        """
        if self.due_time is None:
            return None
        reference_time = current_time or datetime.now()
        delta = self.due_time - reference_time
        return int(delta.total_seconds() // 60)

    def is_stat(self) -> bool:
        """Return True when the order is STAT (highest priority)."""
        return self.status.upper() == "STAT"

    def is_iv(self) -> bool:
        """Return True when the medication route is intravenous (IV)."""
        return self.route.upper() == "IV"

    def update_location(self, room: Optional[int] = None, unit: Optional[str] = None, bin_number: Optional[int] = None) -> None:
        """Update the order's location, preserving the previous location when changed.

        A room change records the former patient location in
        ``previous_location`` so transfer rules can compare it with the
        current location. ``current_bin`` changes only when ``bin_number`` is
        explicitly supplied, because patient movement and physical medication
        movement are separate events.
        """
        if self.location is None:
            self.location = PatientLocation(room=self.room, unit=self.unit or "")
        if room is not None:
            self.previous_location = PatientLocation(room=self.location.room, unit=self.location.unit, bin_number=self.location.bin_number)
            self.location.update_room(room)
            self.room = room
        if unit is not None:
            self.location.update_unit(unit)
            self.unit = unit
        if bin_number is not None:
            self.location.bin_number = bin_number
            self.current_bin = bin_number

    def assign_current_bin(self, bin_number: int | str) -> None:
        """Record the physical bin that currently holds this medication."""
        self.current_bin = bin_number
        if self.location is not None:
            self.location.bin_number = bin_number

    def mark_tubed(self) -> None:
        """Mark this active order as having been tubed."""
        if self.pre_tubing_status is None:
            self.pre_tubing_status = self.status
        self.status = "TUBED"
        self.tubed = True

    def update_status(self, status: str) -> None:
        """Update status while keeping queue-state fields consistent."""
        self.status = status
        normalized_status = status.upper()
        self.tubed = normalized_status == "TUBED"
        if normalized_status in {"COMPLETED", "DONE"}:
            self.active = False

    def get_order_information(self) -> dict:
        """Return a serializable summary of the order suitable for APIs or logging."""
        return {
            "order_id": self.order_id,
            "order_number": self.order_number,
            "patient_id": self.patient_id,
            "medication": self.medication,
            "medication_name": self.medication_name,
            "route": self.route,
            "status": self.status,
            "clinical_status": self.pre_tubing_status or self.status,
            "tubing_status": "TUBED" if self.tubed else "PENDING",
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "room": self.room,
            "unit": self.unit,
            "current_bin": self.current_bin,
            "tubed": self.tubed,
            "active": self.active,
        }
