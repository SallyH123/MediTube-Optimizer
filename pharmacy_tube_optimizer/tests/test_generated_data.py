from datetime import datetime, timedelta

from pharmacy_tube_optimizer.data.medication_data import generate_bins, generate_random_medication_orders
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder


def test_every_randomly_generated_order_is_initially_placed_in_one_bin():
    orders = generate_random_medication_orders(10, seed=42, reference_time=datetime(2026, 8, 11, 12, 0))
    bins = generate_bins(orders)

    placed_order_ids = [
        order.order_id
        for bin_obj in bins
        for order in bin_obj.get_pending_medications()
    ]

    assert len(placed_order_ids) == len(orders)
    assert set(placed_order_ids) == {order.order_id for order in orders}


def test_unknown_bin_holds_active_orders_without_a_valid_bin():
    order = MedicationOrder(order_id="UNKNOWN-1", medication="Test medication", route="PO")

    unknown_bin = next(bin_obj for bin_obj in generate_bins([order]) if bin_obj.bin_number == "UNKNOWN")

    assert unknown_bin.get_pending_medications() == [order]


def test_unknown_bin_holds_orders_with_invalid_placement_information():
    order = MedicationOrder(
        order_id="UNKNOWN-2",
        medication="Test medication",
        route="PO",
        due_time=datetime(2026, 8, 11, 12, 30),
        status="Routine",
        room=8012,
        unit="MICU",
    )

    unknown_bin = next(bin_obj for bin_obj in generate_bins([order]) if bin_obj.bin_number == "UNKNOWN")

    assert unknown_bin.get_pending_medications() == [order]


def test_random_due_times_are_within_six_hours():
    now = datetime(2026, 8, 11, 12, 0)
    orders = generate_random_medication_orders(10, seed=42, reference_time=now)

    assert all(now <= order.due_time <= now + timedelta(minutes=360) for order in orders)
