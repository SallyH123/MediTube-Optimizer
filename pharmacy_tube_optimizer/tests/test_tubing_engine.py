from datetime import datetime

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.services.tubing_engine import TubingEngine


def test_stat_priority():
    engine = TubingEngine()
    stat_order = MedicationOrder(
        order_id="STAT-1",
        medication="Cefepime",
        route="IV",
        due_time=datetime(2026, 8, 2, 10, 0),
        status="STAT",
        room=8012,
        unit="MICU",
    )
    routine_order = MedicationOrder(
        order_id="ROU-1",
        medication="Senna",
        route="PO",
        due_time=datetime(2026, 8, 2, 10, 30),
        status="Routine",
        room=8012,
        unit="MICU",
    )

    bin_obj = Bin(8)
    bin_obj.add_medication(stat_order)
    bin_obj.add_medication(routine_order)

    to_send = engine.evaluate_bin(bin_obj, datetime(2026, 8, 2, 9, 50))

    assert len(to_send) == 2
    assert to_send[0].is_stat() is True


def test_night_cutoff_holds_medication_until_release_time():
    engine = TubingEngine()
    oral_order = MedicationOrder(
        order_id="PO-1",
        medication="Metoprolol",
        route="PO",
        due_time=datetime(2026, 8, 2, 23, 0),
        status="Routine",
        room=8012,
        unit="MICU",
    )

    assert engine.should_tube_medication(oral_order, datetime(2026, 8, 2, 20, 0)) is False
    assert engine.should_tube_medication(oral_order, datetime(2026, 8, 2, 20, 30)) is True


def test_routine_selection():
    engine = TubingEngine()
    iv_order = MedicationOrder(
        order_id="IV-1",
        medication="Vancomycin",
        route="IV",
        due_time=datetime(2026, 8, 2, 10, 15),
        status="Routine",
        room=8012,
        unit="MICU",
    )
    bin_obj = Bin(8)
    bin_obj.add_medication(iv_order)

    to_send = engine.evaluate_bin(bin_obj, datetime(2026, 8, 2, 10, 0))

    assert iv_order in to_send


def test_transferred_order_is_projected_to_destination_bin_without_mutation():
    engine = TubingEngine()
    source_bin = Bin(8)
    destination_bin = Bin(7)
    order = MedicationOrder(
        order_id="TR-1",
        medication="Heparin",
        route="IV",
        due_time=datetime(2026, 8, 2, 10, 30),
        status="Routine",
        room=8012,
        unit="MICU",
    )
    order.previous_location = order.location
    order.update_location(room=7012, unit="SICU")

    source_bin.add_medication(order)

    results = engine.evaluate_all_bins([source_bin, destination_bin], datetime(2026, 8, 2, 10, 0))

    assert 8 not in results
    assert order in results[7]
    assert order in source_bin.get_pending_medications()
    assert order not in destination_bin.get_pending_medications()
    assert order.current_bin == 8


def test_tube_ready_bins_are_ranked_by_bin_priority_score():
    engine = TubingEngine()
    routine_bin = Bin(1)
    stat_bin = Bin(2)
    routine_bin.add_medication(
        MedicationOrder(
            order_id="ROUTINE-1",
            medication="Senna",
            route="PO",
            due_time=datetime(2026, 8, 2, 10, 30),
            status="Routine",
            room=1012,
            unit="MICU",
        )
    )
    stat_bin.add_medication(
        MedicationOrder(
            order_id="STAT-2",
            medication="Cefepime",
            route="IV",
            due_time=datetime(2026, 8, 2, 10, 30),
            status="STAT",
            room=2012,
            unit="MICU",
        )
    )

    recommendations = engine.evaluate_all_bins([routine_bin, stat_bin], datetime(2026, 8, 2, 10, 0))

    assert list(recommendations)[:2] == [2, 1]


def test_only_bins_with_a_closest_due_time_within_one_hour_are_reviewed():
    engine = TubingEngine()
    ready_bin = Bin(1)
    later_bin = Bin(2)
    ready_bin.add_medication(
        MedicationOrder("READY", "Cefepime", "IV", datetime(2026, 8, 2, 10, 30), "Routine", 1012, "MICU")
    )
    later_bin.add_medication(
        MedicationOrder("LATER", "Vancomycin", "IV", datetime(2026, 8, 2, 11, 1), "Routine", 2012, "MICU")
    )

    recommendations = engine.evaluate_all_bins([later_bin, ready_bin], datetime(2026, 8, 2, 10, 0))

    assert recommendations[1][0].order_id == "READY"
    assert 2 not in recommendations


def test_overdue_closest_medication_does_not_change_during_evaluation():
    engine = TubingEngine()
    bin_obj = Bin(1)
    overdue_order = MedicationOrder(
        "OVERDUE", "Cefepime", "IV", datetime(2026, 8, 2, 9, 0), "Routine", 1012, "MICU"
    )
    bin_obj.add_medication(overdue_order)

    engine.evaluate_all_bins([bin_obj], datetime(2026, 8, 2, 10, 0))

    assert overdue_order.due_time == datetime(2026, 8, 2, 9, 0)


def test_missing_transfer_destination_bin_is_projected_without_creating_a_physical_bin():
    engine = TubingEngine()
    source_bin = Bin(8)
    order = MedicationOrder("TR-MISSING", "Heparin", "IV", datetime(2026, 8, 2, 10), "Routine", 8012, "MICU")
    order.previous_location = order.location
    order.update_location(room=7012, unit="SICU")
    source_bin.add_medication(order)
    bins = [source_bin]

    engine.evaluate_all_bins(bins, datetime(2026, 8, 2, 10))

    assert all(bin_obj.bin_number != 7 for bin_obj in bins)
    assert order.current_bin == 8
