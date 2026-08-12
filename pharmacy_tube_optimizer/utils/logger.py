from __future__ import annotations

from datetime import datetime
from typing import Callable


class Logger:
    """In-memory audit logger for tubing workflow events.

    Entries use a concise ``HH:MM - message`` format suitable for a tubing
    board, API response, or future persistent log sink.
    """

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self.events: list[str] = []
        self._clock = clock or datetime.now

    def log_event(self, message: str) -> str:
        """Record an arbitrary workflow event and return the formatted entry."""
        timestamp = self._clock().strftime("%H:%M")
        entry = f"{timestamp} - {message}"
        self.events.append(entry)
        return entry

    def log_bin_evaluation(self, bin_number: int | str) -> str:
        """Record the start of a tubing evaluation for one bin."""
        return self.log_event(f"Evaluating Bin {bin_number}")

    def log_medication_eligibility(self, medication: str, eligible: bool) -> str:
        """Record whether a medication is eligible for tubing."""
        outcome = "eligible for tubing" if eligible else "not eligible for tubing"
        return self.log_event(f"{medication} {outcome}")

    def log_patient_transfer(self, original_room: int | str, current_room: int | str) -> str:
        """Record a patient transfer detected immediately before tubing."""
        return self.log_event(f"Patient transferred {original_room} → {current_room}")

    def log_destination_update(self, original_bin: int | str, destination_bin: int | str) -> str:
        """Record the destination-bin update resulting from a transfer."""
        return self.log_event(f"Destination updated: Bin {original_bin} → Bin {destination_bin}")

    def log_bin_tubed(self, bin_number: int | str, technician: str = "Technician") -> str:
        """Record the technician action that tubed a bin."""
        return self.log_event(f"{technician} tubed Bin {bin_number}")

    def log_medication_tubed(self, medication: str, bin_number: int | str) -> str:
        """Record a medication status change and removal from its source bin."""
        return self.log_event(f"{medication} status changed to TUBED and removed from Bin {bin_number}")

    def get_logs(self) -> list[str]:
        """Return a copy of the event log in chronological order."""
        return list(self.events)

    def clear_logs(self) -> None:
        """Remove all in-memory log entries."""
        self.events.clear()
