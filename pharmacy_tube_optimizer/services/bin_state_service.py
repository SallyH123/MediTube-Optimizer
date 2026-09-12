"""Assemble tubing-board state for presentation layers.

This service deliberately does not evaluate eligibility, transfers, or
priority. Those values are supplied by ``TubingEvaluation`` from the engine.
"""

from __future__ import annotations

from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS, UNKNOWN_BIN
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.rules.priority_rules import calculate_bin_priority_score
from pharmacy_tube_optimizer.services.tubing_engine import TubingEvaluation


class BinStateService:
    """Convert current bins and an engine evaluation into API-safe data."""

    def get_board_state(self, bins: list[Bin], evaluation: TubingEvaluation) -> dict:
        """Return standard bins, UNKNOWN, and engine-detected transfers."""
        bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}
        standard_bins = [
            self._bin_state(bins_by_number.get(bin_number, Bin(bin_number)), evaluation)
            for bin_number in TUBING_BIN_LOCATIONS
            if bin_number != UNKNOWN_BIN
        ]
        unknown_bin = self._bin_state(bins_by_number.get(UNKNOWN_BIN, Bin(UNKNOWN_BIN)), evaluation)
        return {
            "bins": standard_bins,
            "unknown_bin": unknown_bin,
            "detected_transfers": list(evaluation.detected_transfers),
        }

    def get_bin_state(self, bin_id: int | str, bins: list[Bin], evaluation: TubingEvaluation) -> dict | None:
        """Return one standard or UNKNOWN bin, if it is part of the board."""
        normalized_id = self._normalize_bin_id(bin_id)
        if normalized_id not in TUBING_BIN_LOCATIONS:
            return None
        bin_obj = next((candidate for candidate in bins if candidate.bin_number == normalized_id), Bin(normalized_id))
        return self._bin_state(bin_obj, evaluation)

    def _bin_state(self, bin_obj: Bin, evaluation: TubingEvaluation) -> dict:
        """Serialize one physical bin with evaluation-derived readiness data."""
        orders = bin_obj.get_pending_medications()
        ready_order_ids = {
            order.order_id
            for ready_orders in evaluation.ready_bins.values()
            for order in ready_orders
        }
        return {
            "bin_id": bin_obj.bin_id,
            "bin_name": self._bin_name(bin_obj.bin_number),
            "bin_number": str(bin_obj.bin_number),
            "medication_count": len(orders),
            "ready_to_tube": bin_obj.bin_number in evaluation.ready_bins,
            # This is the queue's current priority based on pending orders.
            # It is kept separate from ``priority_score``, which remains the
            # final, ready-to-tube ranking supplied by TubingEvaluation.
            "queue_priority_score": calculate_bin_priority_score([
                {"status": order.status, "route": order.route}
                for order in orders
            ]),
            "priority_score": evaluation.priority_scores.get(bin_obj.bin_number, 0.0),
            "medications": [self._medication_state(order, evaluation, ready_order_ids) for order in orders],
        }

    @staticmethod
    def _medication_state(
        order: MedicationOrder, evaluation: TubingEvaluation, ready_order_ids: set[str]
    ) -> dict:
        """Serialize one medication for safe frontend consumption."""
        return {
            "order_number": order.order_number,
            "medication_name": order.medication_name,
            "room": str(order.room) if order.room is not None else None,
            "unit": order.unit,
            "route": order.route,
            "due_time": order.due_time.isoformat() if order.due_time else None,
            "status": order.status,
            "priority_score": evaluation.medication_priority_scores.get(order.order_id, 0),
            "ready_to_tube": order.order_id in ready_order_ids,
        }

    @staticmethod
    def _normalize_bin_id(bin_id: int | str) -> int | str:
        """Normalize a display bin identifier to its domain value."""
        value = str(bin_id).strip().upper()
        if value.startswith("BIN_"):
            value = value[4:]
        return int(value) if value.isdigit() else value

    @staticmethod
    def _bin_name(bin_number: int | str) -> str:
        """Return the frontend-friendly name for a bin number."""
        return "Unknown destination" if bin_number == UNKNOWN_BIN else f"Bin {bin_number}"
