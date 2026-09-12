"""Evaluate and explicitly execute physical tubing work.

Evaluation is a read-only projection of the current bins.  It may detect a
patient transfer and place that order in its *projected* destination bin, but
does not alter orders or physical bins.  Execution is a separate, explicit
operation that performs the projected moves and marks selected orders tubed.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.rules.cutoff_rules import is_cutoff_released
from pharmacy_tube_optimizer.rules.priority_rules import (
    calculate_bin_priority_score,
    get_medication_priority,
    rank_bins_for_tubing,
)
from pharmacy_tube_optimizer.rules.transfer_rules import get_destination_bin_number, get_transfer_details
from pharmacy_tube_optimizer.rules.tubing_window_rules import (
    is_closest_medication_within_tubing_window,
    is_within_tubing_window,
)
from pharmacy_tube_optimizer.services.medication_service import MedicationService


@dataclass(frozen=True)
class TubingEvaluation:
    """Read-only tubing recommendation, ordered highest priority first."""

    ready_bins: dict[int | str, tuple[MedicationOrder, ...]]
    priority_scores: dict[int | str, float]
    medication_priority_scores: dict[str, int]
    detected_transfers: tuple[dict, ...]

    @property
    def sorted_bin_numbers(self) -> tuple[int | str, ...]:
        """Return the technician's recommended tubing order."""
        return tuple(self.ready_bins)


class TubingEngine:
    """Evaluate bins without mutation, then tube only on an explicit request."""

    def evaluate(self, bins: list[Bin], current_time: datetime) -> TubingEvaluation:
        """Build a transfer-aware, ranked recommendation without changing state.

        The one-hour closest-dose review gate and all existing medication
        eligibility rules remain in force.  Transfers are reconciled only in
        an in-memory projection, so callers can safely render this result and
        wait for a technician/API request before executing it.
        """
        projected_bins = {
            bin_obj.bin_number: list(bin_obj.get_pending_medications())
            for bin_obj in bins
        }
        qualified_bin_numbers = {
            bin_obj.bin_number
            for bin_obj in bins
            if self._is_bin_ready_for_review(bin_obj, current_time)
        }

        bins_to_reconcile = deque(qualified_bin_numbers)
        reconciled_bin_numbers: set[int | str] = set()
        detected_transfers: list[dict] = []
        while bins_to_reconcile:
            source_number = bins_to_reconcile.popleft()
            if source_number in reconciled_bin_numbers:
                continue
            reconciled_bin_numbers.add(source_number)

            for order in list(projected_bins.get(source_number, [])):
                details = get_transfer_details(order)
                if details is None or not details["transferred"]:
                    continue
                destination_number = get_destination_bin_number(details)
                # Once a previous transfer has been physically reconciled,
                # it is not a new transfer event for this evaluation.
                if destination_number == source_number:
                    continue
                detected_transfers.append(
                    {
                        "order_number": order.order_id,
                        "medication_name": order.medication,
                        "old_room": details["original_room"],
                        "new_room": details["current_room"],
                        "old_bin": str(source_number),
                        "new_bin": str(destination_number) if destination_number is not None else None,
                    }
                )
                projected_bins[source_number].remove(order)
                if destination_number is None:
                    # A transfer with no safe destination is withheld from
                    # this evaluation, as it was in the prior workflow.
                    continue

                destination_orders = projected_bins.setdefault(destination_number, [])
                if order not in destination_orders:
                    destination_orders.append(order)
                # A transfer can make a previously non-qualified destination
                # relevant, so its projected contents must also be evaluated.
                if destination_number not in qualified_bin_numbers:
                    qualified_bin_numbers.add(destination_number)
                    bins_to_reconcile.append(destination_number)

        ranked_candidates: list[dict] = []
        for bin_number in qualified_bin_numbers:
            final_orders = self._eligible_orders(projected_bins.get(bin_number, []), current_time)
            if not final_orders:
                continue
            medication_data = [self._priority_payload(order) for order in final_orders]
            ranked_candidates.append(
                {
                    "bin_number": bin_number,
                    "medications": medication_data,
                    "orders": final_orders,
                    "priority_score": calculate_bin_priority_score(medication_data),
                }
            )

        ranked_candidates = rank_bins_for_tubing(ranked_candidates)
        return TubingEvaluation(
            ready_bins={candidate["bin_number"]: tuple(candidate["orders"]) for candidate in ranked_candidates},
            priority_scores={candidate["bin_number"]: candidate["priority_score"] for candidate in ranked_candidates},
            medication_priority_scores={
                order.order_id: self._priority_score(order)
                for orders in projected_bins.values()
                for order in orders
            },
            detected_transfers=tuple(detected_transfers),
        )

    def prepare_tubing(self, bins: list[Bin], current_time: datetime) -> TubingEvaluation:
        """Reconcile transfers, then return a fresh final evaluation.

        This is the explicit state-changing preparation operation used by an
        application/API immediately before displaying or executing tubing.
        The public :meth:`evaluate` method remains read-only.
        """
        projected_evaluation = self.evaluate(bins, current_time)
        if not projected_evaluation.detected_transfers:
            return projected_evaluation

        self.apply_detected_transfers(bins, projected_evaluation.detected_transfers)
        final_evaluation = self.evaluate(bins, current_time)
        return replace(final_evaluation, detected_transfers=projected_evaluation.detected_transfers)

    def apply_detected_transfers(self, bins: list[Bin], transfers: Iterable[dict]) -> None:
        """Apply transfer results previously detected by :meth:`evaluate`.

        This method contains the physical bin movement; callers do not need
        to implement destination or transfer rules themselves.
        """
        bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}
        for transfer in transfers:
            destination_value = transfer.get("new_bin")
            if destination_value is None:
                continue
            destination_number: int | str = int(destination_value) if str(destination_value).isdigit() else str(destination_value)
            order_number = transfer["order_number"]
            source_bin = next(
                (bin_obj for bin_obj in bins if any(order.order_id == order_number for order in bin_obj.get_pending_medications())),
                None,
            )
            if source_bin is None:
                continue
            destination_bin = self._get_or_create_bin(destination_number, bins, bins_by_number)
            if source_bin is destination_bin:
                continue
            order = next(order for order in source_bin.get_pending_medications() if order.order_id == order_number)
            source_bin.remove_medication(order_number)
            destination_bin.add_medication(order)

    def evaluate_all_bins(
        self, bins: list[Bin], current_time: datetime
    ) -> dict[int | str, list[MedicationOrder]]:
        """Compatibility wrapper returning ordered ready bins as lists.

        New callers should use :meth:`evaluate` to also receive scores and
        detected transfers.  Both methods are read-only.
        """
        return {bin_number: list(orders) for bin_number, orders in self.evaluate(bins, current_time).ready_bins.items()}

    def execute_tubing(
        self,
        evaluation: TubingEvaluation,
        bins: list[Bin],
        medication_service: MedicationService,
        selected_bins: Iterable[int | str] | None = None,
    ) -> list[MedicationOrder]:
        """Tube evaluated orders only after an explicit application/API request.

        ``selected_bins`` may restrict execution to a technician-selected
        subset; omitted means execute the full, already-ranked evaluation.
        """
        requested_bins = set(selected_bins) if selected_bins is not None else set(evaluation.ready_bins)
        bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}
        tubed_orders: list[MedicationOrder] = []
        for destination_number, orders in evaluation.ready_bins.items():
            if destination_number not in requested_bins:
                continue
            destination_bin = self._get_or_create_bin(destination_number, bins, bins_by_number)
            for order in orders:
                source_bin = self._find_pending_order_bin(order, bins)
                if source_bin is None:
                    continue
                if source_bin is not destination_bin:
                    source_bin.remove_medication(order.order_id)
                    destination_bin.add_medication(order)
                tubed_orders.append(medication_service.tube_medication(order, destination_bin))
        return tubed_orders

    def execute_manual_tubing(
        self,
        bin_number: int | str,
        bins: list[Bin],
        medication_service: MedicationService,
    ) -> list[MedicationOrder]:
        """Tube every pending order in one bin after an approved override.

        Transfer reconciliation remains the caller's responsibility and is
        deliberately performed before this method.  This operation bypasses
        only the normal eligibility selection for a technician-approved bin.
        """
        bin_obj = next((candidate for candidate in bins if candidate.bin_number == bin_number), None)
        if bin_obj is None:
            return []
        return [
            medication_service.tube_medication(order, bin_obj)
            for order in list(bin_obj.get_pending_medications())
        ]

    def evaluate_bin(
        self, bin_obj: Bin, current_time: datetime, all_bins: list[Bin] | None = None
    ) -> list[MedicationOrder]:
        """Return one bin's read-only projected eligibility result."""
        evaluation = self.evaluate(all_bins if all_bins is not None else [bin_obj], current_time)
        return list(evaluation.ready_bins.get(bin_obj.bin_number, ()))

    def should_tube_medication(self, order: MedicationOrder, current_time: datetime) -> bool:
        """Return whether one medication passes cutoff and timing-window rules."""
        if order.due_time is not None and not is_cutoff_released(current_time, order.due_time):
            return False
        return self.is_within_tubing_window(order, current_time)

    def is_within_tubing_window(self, order: MedicationOrder, current_time: datetime) -> bool:
        """Return whether an order meets its unit-specific timing window."""
        if order.due_time is None:
            return True
        unit = self._get_order_unit(order)
        return not unit or is_within_tubing_window(current_time, order.due_time, unit)

    def select_medications_to_send(self, bin_obj: Bin) -> list[MedicationOrder]:
        """Return pending medications ordered by priority only."""
        return self._sort_by_priority(list(bin_obj.get_pending_medications()))

    def _eligible_orders(self, orders: list[MedicationOrder], current_time: datetime) -> list[MedicationOrder]:
        """Filter a projected queue to tube-eligible orders and rank them."""
        return self._sort_by_priority([order for order in orders if self.should_tube_medication(order, current_time)])

    @staticmethod
    def _is_bin_ready_for_review(bin_obj: Bin, current_time: datetime) -> bool:
        """Return whether the bin's closest due medication opens review."""
        return is_closest_medication_within_tubing_window(list(bin_obj.get_pending_medications()), current_time)

    @staticmethod
    def _get_or_create_bin(
        bin_number: int | str, bins: list[Bin], bins_by_number: dict[int | str, Bin]
    ) -> Bin:
        """Return a destination bin, creating it when the destination is new."""
        destination_bin = bins_by_number.get(bin_number)
        if destination_bin is None:
            destination_bin = Bin(bin_number)
            bins.append(destination_bin)
            bins_by_number[bin_number] = destination_bin
        return destination_bin

    @staticmethod
    def _find_pending_order_bin(order: MedicationOrder, bins: list[Bin]) -> Bin | None:
        """Find the physical bin that currently contains a pending order."""
        return next((bin_obj for bin_obj in bins if order in bin_obj.get_pending_medications()), None)

    def _sort_by_priority(self, orders: list[MedicationOrder]) -> list[MedicationOrder]:
        """Return orders in descending medication-priority order."""
        return sorted(orders, key=lambda order: self._priority_score(order), reverse=True)

    def _priority_score(self, order: MedicationOrder) -> int:
        """Calculate the existing priority-rule score for one order."""
        return get_medication_priority(order.status, order.route)

    @staticmethod
    def _get_order_unit(order: MedicationOrder) -> str:
        """Resolve the unit used for timing-window evaluation."""
        if order.location is not None and order.location.unit:
            return order.location.unit
        return order.unit or ""

    @staticmethod
    def _priority_payload(order: MedicationOrder) -> dict[str, str]:
        """Build the minimal rule input used for bin-priority scoring."""
        return {"status": order.status, "route": order.route}
