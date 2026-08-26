"""Application entry point for MediTube Optimizer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from random import Random
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pharmacy_tube_optimizer.data.mock_data_generator import generate_random_mock_dataset
from pharmacy_tube_optimizer.data.transfer_data import generate_random_patient_transfer
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.rules.transfer_rules import check_transfer_before_tubing
from pharmacy_tube_optimizer.services.tubing_engine import TubingEngine, TubingEvaluation
from pharmacy_tube_optimizer.utils.logger import Logger


def _due_time_text(order: MedicationOrder) -> str:
    return order.due_time.strftime("%Y-%m-%d %H:%M") if order.due_time else "No due time"


def display_tubing_board(evaluation: TubingEvaluation) -> None:
    """Print the read-only, priority-sorted tubing recommendation."""
    print("\nTubing Board")
    print("=" * 12)
    if not evaluation.ready_bins:
        print("No bins are currently ready to tube.")
        return
    for bin_number, orders in evaluation.ready_bins.items():
        medications = ", ".join(f"{order.medication} ({order.order_id})" for order in orders)
        print(f"Bin {bin_number} | priority {evaluation.priority_scores[bin_number]}: {medications}")


def display_generated_data(orders: list[MedicationOrder], bins: list, heading: str = "Generated") -> None:
    """Print orders and each non-empty physical bin with full order details."""
    print(f"\n{heading} Medication Orders")
    print("=" * 27)
    for order in orders:
        print(
            f"order ID {order.order_id} | med {order.medication} | route {order.route} | "
            f"due {_due_time_text(order)} | room {order.room} | bin {order.current_bin} | "
            f"tubed {'Yes' if order.tubed else 'No'}"
        )

    print(f"\n{heading} Bins")
    print("=" * 14)
    for bin_obj in bins:
        pending_orders = bin_obj.get_pending_medications()
        if not pending_orders:
            continue
        print(f"Bin {bin_obj.bin_number}:")
        for order in pending_orders:
            print(
                f"  order ID {order.order_id} | med {order.medication} | route {order.route} | "
                f"status {order.status} | due {_due_time_text(order)} | room {order.room}"
            )


def run_application(
    current_time: datetime | None = None, *, display: bool = True, seed: int | None = None, order_count: int = 10
) -> dict[str, Any]:
    """Generate orders, show bins before and after one random patient transfer."""
    evaluation_time = current_time or datetime.now()
    logger = Logger()
    database, bins, orders = generate_random_mock_dataset(order_count, seed=seed, reference_time=evaluation_time)
    logger.log_event(f"Loaded {len(orders)} medication orders")

    if display:
        print("MediTube Optimizer starting...")
        print(f"Evaluation time: {evaluation_time:%Y-%m-%d %H:%M}")
        display_generated_data(orders, bins, heading="Original Generated")

    # The transfer always selects an order from this generated order list. Its
    # physical medication remains in the source bin until the engine moves it.
    transferred_order, destination_room, destination_bin = generate_random_patient_transfer(orders, rng=Random(seed))
    original_room = transferred_order.previous_location.room if transferred_order.previous_location else None
    transfer = check_transfer_before_tubing(str(original_room), str(destination_room))
    logger.log_patient_transfer(transfer["original_room"], transfer["current_room"])
    logger.log_destination_update(transfer["original_bin"], destination_bin)

    engine = TubingEngine()
    for bin_obj in bins:
        logger.log_bin_evaluation(bin_obj.bin_number)
    evaluation = engine.evaluate(bins, evaluation_time)
    recommendations = {bin_number: list(orders) for bin_number, orders in evaluation.ready_bins.items()}
    for candidate_orders in evaluation.ready_bins.values():
        for order in candidate_orders:
            logger.log_medication_eligibility(order.medication, True)

    if display:
        print(
            f"\nGenerated Transfer: order ID {transferred_order.order_id} | "
            f"room {original_room} -> {destination_room} | bin {transfer['original_bin']} -> {destination_bin}"
        )
        display_generated_data(orders, bins, heading="Generated After Transfer (Not Tubed)")
        display_tubing_board(evaluation)
        print("\nRecommendation complete. Awaiting an explicit tubing request.")

    return {
        "database": database,
        "orders": orders,
        "patient_locations": {transferred_order.order_id: str(destination_room)},
        "transfers": [transfer],
        "evaluation": evaluation,
        "recommendations": recommendations,
        "tubed_orders": [],
        "tubed_order_priority_scores": {},
        "logs": logger.get_logs(),
    }


def main() -> None:
    run_application()


if __name__ == "__main__":
    main()
