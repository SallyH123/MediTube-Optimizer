from datetime import datetime, timedelta

from pharmacy_tube_optimizer.data.medication_data import (
    generate_bins,
    generate_medication_orders,
    generate_random_medication_orders,
)
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.config import ROOM_PREFIX_BIN_MAP


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


def test_seeded_orders_use_room_mapped_units_and_stay_out_of_unknown():
    orders = generate_medication_orders()
    bins = generate_bins(orders)
    bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}

    assert bins_by_number["UNKNOWN"].get_pending_medications() == []
    assert bins_by_number["ED"].get_pending_medications()[0].order_id == "ROUTINE-IV-8"
    assert {order.order_id for order in bins_by_number[7].get_pending_medications()} == {"STAT-7", "TRANSFER-7-TO-8"}
    assert bins_by_number[6].get_pending_medications()[0].order_id == "ROUTINE-PO-6"
    assert all(
        str(order.unit).upper() == str(ROOM_PREFIX_BIN_MAP[str(order.room)[0]]).upper()
        for order in orders
    )
