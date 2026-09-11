import json
from datetime import datetime
from io import BytesIO

from pharmacy_tube_optimizer.api.app import create_app
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder


NOW = datetime(2026, 8, 2, 10, 0)


def _request(app, method: str, path: str) -> tuple[str, dict]:
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path, "wsgi.input": BytesIO()}, start_response))
    return captured["status"], json.loads(body)


def _transferred_order() -> tuple[list[Bin], list[MedicationOrder]]:
    source_bin, destination_bin = Bin(8), Bin(7)
    order = MedicationOrder("ORD001", "Cefepime", "IV", NOW.replace(minute=30), "Routine", 8012, "ED")
    order.previous_location = order.location
    order.update_location(room=7015, unit="SICU")
    source_bin.add_medication(order)
    return [source_bin, destination_bin], [order]


def test_get_bins_returns_board_state_and_reconciled_transfer():
    bins, orders = _transferred_order()
    app = create_app(bins, orders, clock=lambda: NOW)

    status, payload = _request(app, "GET", "/bins")

    assert status == "200 OK"
    bin_seven = next(item for item in payload["bins"] if item["bin_number"] == "7")
    assert bin_seven["ready_to_tube"] is True
    assert bin_seven["medication_count"] == 1
    assert bin_seven["medications"][0]["order_number"] == "ORD001"
    assert bin_seven["medications"][0]["ready_to_tube"] is True
    assert bin_seven["medications"][0]["priority_score"] == 30
    assert payload["detected_transfers"] == [
        {
            "order_number": "ORD001",
            "medication_name": "Cefepime",
            "old_room": "8012",
            "new_room": "7015",
            "old_bin": "8",
            "new_bin": "7",
        }
    ]
    assert orders[0].current_bin == 7


def test_get_bins_retains_the_latest_backend_detected_transfer_after_reconciliation():
    bins, orders = _transferred_order()
    app = create_app(bins, orders, clock=lambda: NOW)

    _, first_payload = _request(app, "GET", "/bins")
    _, second_payload = _request(app, "GET", "/bins")

    assert second_payload["detected_transfers"] == first_payload["detected_transfers"]


def test_get_one_bin_and_post_tube_return_updated_state():
    bins, orders = _transferred_order()
    app = create_app(bins, orders, clock=lambda: NOW)

    status, bin_payload = _request(app, "GET", "/bins/7")
    assert status == "200 OK"
    assert bin_payload["bin"]["bin_id"] == "BIN_7"

    status, tube_payload = _request(app, "POST", "/bins/7/tube")

    assert status == "200 OK"
    assert tube_payload["tubed_order_numbers"] == ["ORD001"]
    assert tube_payload["detected_transfers"] == []
    assert orders[0].tubed is True
    assert tube_payload["tubed_medications"] == [
        {
            "order_id": "ORD001",
            "order_number": "ORD001",
            "patient_id": "",
            "medication": "Cefepime",
            "medication_name": "Cefepime",
            "route": "IV",
            "status": "TUBED",
            "clinical_status": "Routine",
            "tubing_status": "TUBED",
            "due_time": "2026-08-02T10:30:00",
            "room": 7015,
            "unit": "SICU",
            "current_bin": 7,
            "tubed": True,
            "active": True,
        }
    ]
    bin_seven = next(item for item in tube_payload["bins"] if item["bin_number"] == "7")
    assert bin_seven["medication_count"] == 0

    status, second_tube_payload = _request(app, "POST", "/bins/7/tube")

    assert status == "200 OK"
    assert second_tube_payload["tubed_order_numbers"] == []
    assert [item["order_number"] for item in second_tube_payload["tubed_medications"]] == ["ORD001"]


def test_unknown_bin_is_returned_separately():
    order = MedicationOrder("UNKNOWN-1", "Cefepime", "IV", NOW.replace(minute=30), "Routine")
    unknown_bin = Bin("UNKNOWN")
    unknown_bin.add_medication(order)
    app = create_app([unknown_bin], [order], clock=lambda: NOW)

    status, payload = _request(app, "GET", "/bins")

    assert status == "200 OK"
    assert payload["unknown_bin"]["bin_id"] == "BIN_UNKNOWN"
    assert payload["unknown_bin"]["medication_count"] == 1


def test_get_bins_exposes_a_backend_queue_priority_for_non_ready_bins():
    later_order = MedicationOrder("LATER-1", "Cefepime", "IV", NOW.replace(hour=11, minute=1), "STAT", 7015, "7")
    app = create_app([Bin(7, pending_medications=[later_order])], [later_order], clock=lambda: NOW)

    status, payload = _request(app, "GET", "/bins")
    bin_seven = next(item for item in payload["bins"] if item["bin_number"] == "7")

    assert status == "200 OK"
    assert bin_seven["ready_to_tube"] is False
    assert bin_seven["priority_score"] == 0.0
    assert bin_seven["queue_priority_score"] == 195.0


def test_get_bins_marks_only_eligible_medications_for_tubing():
    ready_order = MedicationOrder("READY-1", "Cefepime", "IV", NOW.replace(minute=30), "Routine", 7015, "7")
    held_order = MedicationOrder("HELD-1", "Vancomycin", "PO", NOW.replace(hour=16), "Routine", 7015, "7")
    app = create_app([Bin(7, pending_medications=[ready_order, held_order])], [ready_order, held_order], clock=lambda: NOW)

    status, payload = _request(app, "GET", "/bins")
    bin_seven = next(item for item in payload["bins"] if item["bin_number"] == "7")
    medications = {item["order_number"]: item for item in bin_seven["medications"]}

    assert status == "200 OK"
    assert bin_seven["ready_to_tube"] is True
    assert medications["READY-1"]["ready_to_tube"] is True
    assert medications["HELD-1"]["ready_to_tube"] is False


def test_force_tube_tubes_all_pending_medications_in_a_non_ready_bin():
    held_order = MedicationOrder("FORCE-1", "Cefepime", "IV", NOW.replace(hour=11, minute=1), "Routine", 7015, "7")
    bin_seven = Bin(7)
    bin_seven.add_medication(held_order)
    app = create_app([bin_seven], [held_order], clock=lambda: NOW)

    status, initial_board = _request(app, "GET", "/bins")
    initial_bin = next(item for item in initial_board["bins"] if item["bin_number"] == "7")
    assert status == "200 OK"
    assert initial_bin["ready_to_tube"] is False

    status, payload = _request(app, "POST", "/bins/7/force-tube")

    assert status == "200 OK"
    assert payload["manual_override"]["approved"] is True
    assert payload["tubed_order_numbers"] == ["FORCE-1"]
    assert held_order.tubed is True
    assert bin_seven.get_pending_medications() == []
    assert payload["tubed_medications"][0]["order_number"] == "FORCE-1"


def test_simulation_refresh_appends_unique_orders_and_preserves_existing_state():
    pending_order = MedicationOrder("EXISTING-PENDING", "Cefepime", "IV", NOW.replace(hour=11, minute=1), "Routine", 7015, "7")
    tubed_order = MedicationOrder("EXISTING-TUBED", "Vancomycin", "PO", NOW, "STAT", 6015, "6")
    tubed_order.mark_tubed()
    bin_seven = Bin(7)
    bin_seven.add_medication(pending_order)
    app = create_app([bin_seven], [pending_order, tubed_order], clock=lambda: NOW)

    status, payload = _request(app, "POST", "/simulation/refresh")

    assert status == "200 OK"
    assert len(payload["generated_order_numbers"]) == 10
    assert len(set(payload["generated_order_numbers"])) == 10
    assert not ({"EXISTING-PENDING", "EXISTING-TUBED"} & set(payload["generated_order_numbers"]))
    assert len(app.medication_service.orders) == 12
    assert pending_order in bin_seven.get_pending_medications()
    assert pending_order.tubed is False
    assert tubed_order.tubed is True
    assert [order["order_number"] for order in payload["tubed_medications"]] == ["EXISTING-TUBED"]
    assert len(payload["detected_transfers"]) == 1
    assert payload["detected_transfers"][0]["old_room"] != payload["detected_transfers"][0]["new_room"]
