"""
override_service.py

Handles the human override workflow for tubing decisions.

This service is responsible for:
    - allowing a technician to manually request tubing for a bin or medication
    - validating that the requested override is still valid
    - reporting whether a bin or medication currently has an override

This module does NOT decide:
    - whether a medication should be tubed by default
    - cutoff eligibility
    - medication priority
    - transfer destination
"""

from __future__ import annotations

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.utils.logger import Logger


class OverrideService:
    """Manage technician overrides for tubing decisions."""

    def __init__(self, logger: Logger | None = None) -> None:
        self.logger = logger or Logger()
        self.override_state: dict[str, bool] = {}

    def override_tubing_decision(self, bin_obj: Bin, medication: MedicationOrder | None = None) -> dict:
        """Allow a technician to manually request tubing for a bin or medication."""
        target_key = medication.order_id if medication is not None else f"bin:{bin_obj.bin_number}"
        self.override_state[target_key] = True
        message = f"Override applied for {target_key}"
        self.record_override(message)
        return {"approved": True, "target": target_key, "message": message}

    def validate_override(self, bin_obj: Bin, medication: MedicationOrder | None = None) -> bool:
        """Validate that the technician request is still usable."""
        if medication is None:
            return bin_obj is not None

        if medication.status.upper() in {"TUBED", "COMPLETED", "DONE"}:
            return False

        return True

    def get_override_status(self, target_key: str) -> bool:
        """Return whether the target currently has an override."""
        return self.override_state.get(target_key, False)

    def record_override(self, message: str) -> None:
        """Record an override event for audit or display purposes."""
        self.logger.log_event(message)
