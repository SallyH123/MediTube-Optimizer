from datetime import datetime

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.main import run_application
from pharmacy_tube_optimizer.services.medication_service import MedicationService
from pharmacy_tube_optimizer.services.tubing_engine import TubingEngine


def test_evaluation_is_read_only_and_execution_is_explicit():
    order = MedicationOrder("READY-1", "Cefepime", "IV", datetime(2026, 8, 2, 10, 30), "Routine", 7012, "SICU")
    bin_obj = Bin(7)
    bin_obj.add_medication(order)
    engine = TubingEngine()

    evaluation = engine.evaluate([bin_obj], datetime(2026, 8, 2, 10))

    assert evaluation.sorted_bin_numbers == (7,)
    assert evaluation.priority_scores[7] > 0
    assert order.tubed is False
    assert order in bin_obj.get_pending_medications()

    tubed_orders = engine.execute_tubing(evaluation, [bin_obj], MedicationService([order]))

    assert tubed_orders == [order]
    assert order.tubed is True
    assert bin_obj.get_pending_medications() == []


def test_demo_evaluates_but_never_automatically_tubes():
    result = run_application(datetime(2026, 8, 2, 10), display=False, seed=42)

    assert result["tubed_orders"] == []
    assert all(order.tubed is False for order in result["orders"])
