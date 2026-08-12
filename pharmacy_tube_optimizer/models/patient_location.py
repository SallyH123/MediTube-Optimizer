"""Lightweight patient-location value model.

``PatientLocation`` records a room, clinical unit, and the numeric tubing bin
derived from that room. It is stored on medication orders to support transfer
checks without requiring a separate patient model.
"""

from __future__ import annotations

from dataclasses import dataclass

from pharmacy_tube_optimizer.config import ROOM_PREFIX_BIN_MAP


@dataclass
class PatientLocation:
    """Current or previous room and unit information for a medication order."""

    room: int | None = None
    unit: str = ""
    bin_number: int | str | None = None

    @staticmethod
    def get_bin_number_from_room(room: int | None) -> int | str | None:
        """Derive the physical tubing bin from the first digit of a room."""
        if room is None:
            return None
        digits = str(room)
        if digits:
            return ROOM_PREFIX_BIN_MAP.get(digits[0])
        return None

    def get_bin_number(self) -> int | str | None:
        """Return the explicit bin, or derive one from the stored room."""
        if self.bin_number is not None:
            return self.bin_number
        return self.get_bin_number_from_room(self.room)

    def update_room(self, room: int) -> None:
        """Set the room and refresh its derived tubing-bin number."""
        self.room = room
        self.bin_number = self.get_bin_number_from_room(room)

    def update_unit(self, unit: str) -> None:
        """Set the clinical-unit label associated with this location."""
        self.unit = unit
