"""Evaluate and rank physical tubing bins.

The engine reviews only bins whose closest pending medication is due within
one hour (including overdue medications). It reconciles patient transfers,
filters each qualifying bin by cutoff and medication-window rules, and ranks
the bins that are ready to tube.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime

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


class TubingEngine:
    """Build a ranked list of bins that are currently ready for tubing."""

    def evaluate_all_bins(
        self, bins: list[Bin], current_time: datetime
    ) -> dict[int | str, list[MedicationOrder]]:
        """Return only tube-ready bins, in highest-priority-first order.

        The method does not process bins whose closest pending dose is more
        than one hour away. A transfer destination is added to the review set
        even if it did not independently meet the one-hour timing gate.
        """
        # Index physical bins for quick transfer-destination lookups.
        bins_by_number: dict[int | str, Bin] = {bin_obj.bin_number: bin_obj for bin_obj in bins}

        # The one-hour closest-dose gate limits processing to bins that need
        # attention now; bins with only later medications are not evaluated.
        qualified_bin_numbers = {
            bin_obj.bin_number
            for bin_obj in bins
            if self._is_bin_ready_for_review(bin_obj, current_time)
        }

        # A transferred medication can make its destination bin relevant, so
        # process qualified bins through a queue rather than one fixed pass.
        bins_to_reconcile = deque(qualified_bin_numbers)
        reconciled_bin_numbers: set[int | str] = set()
        while bins_to_reconcile:
            bin_number = bins_to_reconcile.popleft()
            if bin_number in reconciled_bin_numbers:
                continue
            reconciled_bin_numbers.add(bin_number)
            bin_obj = bins_by_number[bin_number]

            # Reconcile all pending orders before medication eligibility so a
            # medication is never evaluated for tubing at a stale location.
            for order in list(bin_obj.get_pending_medications()):
                transfer_details = get_transfer_details(order)
                if transfer_details is None or not transfer_details["transferred"]:
                    continue

                destination_number = get_destination_bin_number(transfer_details)
                if destination_number is None:
                    # Do not tube to the stale source bin when transfer data
                    # cannot identify a valid destination.
                    bin_obj.remove_medication(order.order_id)
                    continue

                destination_bin = self._get_or_create_bin(destination_number, bins, bins_by_number)
                if destination_bin is bin_obj:
                    # The physical medication is already in its correct bin.
                    continue

                # Remove from the source before adding to the destination to
                # ensure one physical medication belongs to only one bin.
                bin_obj.remove_medication(order.order_id)
                destination_bin.add_medication(order)
                if destination_bin.bin_number not in qualified_bin_numbers:
                    # Destination bins are evaluated even if their closest
                    # pre-transfer medication was more than one hour away.
                    qualified_bin_numbers.add(destination_bin.bin_number)
                    bins_to_reconcile.append(destination_bin.bin_number)

        ranked_candidates: list[dict] = []
        for bin_obj in bins:
            if bin_obj.bin_number not in qualified_bin_numbers:
                continue

            # Only medications passing both individual cutoff and window rules
            # are included in the final tubing candidate list.
            final_orders = self._eligible_orders(bin_obj, current_time)
            if not final_orders:
                continue

            # Priority rules operate on small status/route dictionaries rather
            # than on the full medication-order model.
            medication_data = [self._priority_payload(order) for order in final_orders]
            ranked_candidates.append(
                {
                    "bin_number": bin_obj.bin_number,
                    "medications": medication_data,
                    "orders": final_orders,
                    "priority_score": calculate_bin_priority_score(medication_data),
                }
            )

        # Apply the shared bin-priority rule to set the technician's tubing order.
        ranked_candidates = rank_bins_for_tubing(ranked_candidates)
        return {candidate["bin_number"]: candidate["orders"] for candidate in ranked_candidates}

    def evaluate_bin(
        self, bin_obj: Bin, current_time: datetime, all_bins: list[Bin] | None = None
    ) -> list[MedicationOrder]:
        """Evaluate one bin using the same one-hour timing gate and eligibility rules.

        If a transferred medication has a destination missing from ``all_bins``,
        a new physical bin is created and appended to that list.
        """
        if not self._is_bin_ready_for_review(bin_obj, current_time):
            # Do not perform transfer or eligibility work for later bins.
            return []

        # ``all_bins`` lets a direct caller retain newly created transfer bins.
        bins = all_bins if all_bins is not None else [bin_obj]
        bins_by_number = {candidate.bin_number: candidate for candidate in bins}
        self._reconcile_bin_transfers(bin_obj, bins, bins_by_number)
        return self._eligible_orders(bin_obj, current_time)

    def should_tube_medication(self, order: MedicationOrder, current_time: datetime) -> bool:
        """Return whether one medication passes cutoff and tubing-window rules.

        The due-time cutoff applies to every route, including IV and STAT.
        When the cutoff is released, the normal unit-specific tubing-window
        rule determines whether the medication can be sent.
        """
        if order.due_time is not None and not is_cutoff_released(current_time, order.due_time):
            # A held medication does not proceed to the normal tubing window.
            return False
        return self.is_within_tubing_window(order, current_time)

    def is_within_tubing_window(self, order: MedicationOrder, current_time: datetime) -> bool:
        """Return whether an order is within its unit-specific tubing window."""
        if order.due_time is None:
            # An unscheduled order has no timing-window restriction.
            return True
        unit = self._get_order_unit(order)
        if not unit:
            # Without unit data, use the safe legacy behavior of permitting
            # window evaluation to continue rather than failing the order.
            return True
        return is_within_tubing_window(current_time, order.due_time, unit)

    def select_medications_to_send(self, bin_obj: Bin) -> list[MedicationOrder]:
        """Return the pending medications in one bin, ordered by priority only."""
        return self._sort_by_priority(list(bin_obj.get_pending_medications()))

    def _eligible_orders(self, bin_obj: Bin, current_time: datetime) -> list[MedicationOrder]:
        """Return this bin's medications that pass individual eligibility checks."""
        # Preserve medication ordering within a qualified bin for board display.
        return self._sort_by_priority(
            [
                order
                for order in bin_obj.get_pending_medications()
                if self.should_tube_medication(order, current_time)
            ]
        )

    def _is_bin_ready_for_review(self, bin_obj: Bin, current_time: datetime) -> bool:
        """Return whether the bin's closest pending dose is within one hour."""
        return is_closest_medication_within_tubing_window(
            list(bin_obj.get_pending_medications()), current_time
        )

    def _reconcile_bin_transfers(
        self, source_bin: Bin, bins: list[Bin], bins_by_number: dict[int | str, Bin]
    ) -> None:
        """Move transfers out of one bin, creating missing destination bins."""
        for order in list(source_bin.get_pending_medications()):
            transfer_details = get_transfer_details(order)
            if transfer_details is None or not transfer_details["transferred"]:
                continue
            destination_number = get_destination_bin_number(transfer_details)
            if destination_number is None:
                # A confirmed transfer without a destination is removed from
                # the stale source bin and withheld from tubing.
                source_bin.remove_medication(order.order_id)
                continue
            destination_bin = self._get_or_create_bin(destination_number, bins, bins_by_number)
            if destination_bin is source_bin:
                continue
            source_bin.remove_medication(order.order_id)
            destination_bin.add_medication(order)

    @staticmethod
    def _get_or_create_bin(
        bin_number: int | str, bins: list[Bin], bins_by_number: dict[int | str, Bin]
    ) -> Bin:
        """Return a physical bin, creating it if transfer data references a new one."""
        destination_bin = bins_by_number.get(bin_number)
        if destination_bin is None:
            # This fallback supports incomplete caller-supplied bin lists;
            # normal data generation pre-creates every configured physical bin.
            destination_bin = Bin(bin_number)
            bins.append(destination_bin)
            bins_by_number[bin_number] = destination_bin
        return destination_bin

    def _sort_by_priority(self, orders: list[MedicationOrder]) -> list[MedicationOrder]:
        """Sort orders by medication priority, highest first."""
        # Python's stable sort retains original order when scores are tied.
        return sorted(orders, key=lambda order: self._priority_score(order), reverse=True)

    def _priority_score(self, order: MedicationOrder) -> int:
        """Return the configured status-and-route priority for an order."""
        return get_medication_priority(order.status, order.route)

    @staticmethod
    def _get_order_unit(order: MedicationOrder) -> str:
        """Return the unit stored on the current location or the order itself."""
        if order.location is not None and order.location.unit:
            return order.location.unit
        return order.unit or ""

    @staticmethod
    def _priority_payload(order: MedicationOrder) -> dict[str, str]:
        """Adapt a medication order to the shared priority-rule input shape."""
        return {"status": order.status, "route": order.route}
