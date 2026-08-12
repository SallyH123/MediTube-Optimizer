from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.services.medication_service import MedicationService


def test_iv_priority_over_oral():
    service = MedicationService()

    iv_bin = Bin(8)
    oral_bin = Bin(7)

    iv_order = MedicationOrder(order_id="IV-2", medication="Piperacillin", route="IV", status="Routine", room=8012, unit="MICU")
    oral_order = MedicationOrder(order_id="PO-2", medication="Metformin", route="PO", status="Routine", room=7015, unit="SICU")

    iv_bin.add_medication(iv_order)
    oral_bin.add_medication(oral_order)

    assert service.calculate_bin_priority(iv_bin) > service.calculate_bin_priority(oral_bin)
