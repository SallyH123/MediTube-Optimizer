"""End-to-end coverage for the pharmacy tubing workflow.

These tests deliberately assemble real domain objects and call the real
``TubingEngine`` and WSGI API.  They do not replicate eligibility, transfer,
or priority logic in test helpers.
"""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO

from pharmacy_tube_optimizer.api.app import create_app
from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS, UNKNOWN_BIN
from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.rules.priority_rules import calculate_bin_priority_score
from pharmacy_tube_optimizer.services.tubing_engine import TubingEngine


NOW = datetime(2026, 8, 2, 10, 0)


def _order(
    order_id: str,
    *,
    route: str = "IV",
    status: str = "Routine",
    room: int = 7015,
    unit: str = "SICU",
    due_time: datetime | None = None,
) -> MedicationOrder:
    return MedicationOrder(
        order_id,
        "Cefepime",
        route,
        due_time or NOW.replace(minute=30),
        status,
        room,
        unit,
    )


def _transfer(order: MedicationOrder, *, room: int = 7015, unit: str = "SICU") -> None:
    order.previous_location = order.location
    order.update_location(room=room, unit=unit)


def _request(app, method: str, path: str) -> tuple[str, dict]:
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path, "wsgi.input": BytesIO()}, start_response))
    return captured["status"], json.loads(body)


def _bin_state(payload: dict, bin_number: int | str) -> dict:
    if bin_number == UNKNOWN_BIN:
        return payload["unknown_bin"]
    return next(item for item in payload["bins"] if item["bin_number"] == str(bin_number))


def test_ready_bins_are_finalized_then_ranked_by_existing_priority_rules():
    high_priority_bin, lower_priority_bin, not_ready_bin = Bin(4), Bin(5), Bin(6)
    high_priority_bin.add_medication(_order("HIGH-IV", status="STAT", route="IV", room=4012, unit="4"))
    high_priority_bin.add_medication(_order("HIGH-SUBQ", status="STAT", route="SubQ", room=4013, unit="4"))
    lower_priority_bin.add_medication(_order("LOW-IV", route="IV", room=5012, unit="5"))
    not_ready_bin.add_medication(_order("LATER-STAT", status="STAT", room=6012, unit="6", due_time=NOW.replace(hour=11, minute=1)))

    evaluation = TubingEngine().evaluate([high_priority_bin, lower_priority_bin, not_ready_bin], NOW)

    assert evaluation.sorted_bin_numbers == (4, 5)
    assert 6 not in evaluation.priority_scores
    assert evaluation.priority_scores[4] == calculate_bin_priority_score(
        [{"status": "STAT", "route": "IV"}, {"status": "STAT", "route": "SubQ"}]
    )
    assert evaluation.priority_scores[4] > evaluation.priority_scores[5]


def test_transfer_from_ready_bin_moves_order_and_re_evaluates_both_bins():
    source, destination = Bin("ED"), Bin(7)
    cefepime = _order("TRANSFER-1", room=8012, unit="ED")
    _transfer(cefepime)
    source.add_medication(cefepime)

    evaluation = TubingEngine().prepare_tubing([source, destination], NOW)

    assert source.get_pending_medications() == []
    assert destination.get_pending_medications() == [cefepime]
    assert "ED" not in evaluation.ready_bins
    assert evaluation.ready_bins[7] == (cefepime,)
    assert evaluation.detected_transfers[0]["old_bin"] == "ED"
    assert evaluation.detected_transfers[0]["new_bin"] == "7"


def test_transferring_one_order_does_not_remove_an_old_bin_that_remains_ready():
    source, destination = Bin("ED"), Bin(7)
    transferred = _order("TRANSFER-2", room=8012, unit="ED")
    _transfer(transferred)
    remaining = _order("REMAINS-8", room=8013, unit="ED")
    source.add_medication(transferred)
    source.add_medication(remaining)

    evaluation = TubingEngine().prepare_tubing([source, destination], NOW)

    assert source.get_pending_medications() == [remaining]
    assert destination.get_pending_medications() == [transferred]
    assert evaluation.ready_bins["ED"] == (remaining,)
    assert evaluation.ready_bins[7] == (transferred,)


def test_transfer_to_previously_non_ready_bin_is_scored_only_after_reconciliation():
    source, destination = Bin("ED"), Bin(7)
    transferred = _order("TRANSFER-3", room=8012, unit="ED")
    _transfer(transferred)
    source.add_medication(transferred)
    engine = TubingEngine()

    projected = engine.evaluate([source, destination], NOW)
    assert 7 in projected.ready_bins
    assert projected.priority_scores[7] > 0
    assert destination.get_pending_medications() == []  # evaluation remains read-only

    final = engine.prepare_tubing([source, destination], NOW)
    assert destination.get_pending_medications() == [transferred]
    assert final.ready_bins[7] == (transferred,)


def test_transfer_to_unknown_moves_order_to_the_separate_unknown_bin():
    source, unknown = Bin("ED"), Bin(UNKNOWN_BIN)
    transferred = _order("TRANSFER-UNKNOWN", room=8012, unit="ED")
    _transfer(transferred, room=0, unit="")
    source.add_medication(transferred)

    TubingEngine().prepare_tubing([source, unknown], NOW)

    assert source.get_pending_medications() == []
    assert unknown.get_pending_medications() == [transferred]
    assert transferred.current_bin == UNKNOWN_BIN


def test_api_tube_rechecks_transfer_immediately_before_tubing():
    source, destination = Bin("ED"), Bin(7)
    cefepime = _order("FINAL-CHECK", room=8012, unit="ED")
    source.add_medication(cefepime)
    engine = TubingEngine()
    assert engine.evaluate([source, destination], NOW).ready_bins["ED"] == (cefepime,)

    _transfer(cefepime)
    app = create_app([source, destination], [cefepime], clock=lambda: NOW)
    status, payload = _request(app, "POST", "/bins/7/tube")

    assert status == "200 OK"
    assert payload["tubed_order_numbers"] == ["FINAL-CHECK"]
    assert cefepime.tubed is True
    assert source.get_pending_medications() == []
    assert destination.get_pending_medications() == []
    assert payload["detected_transfers"] == []


def test_cutoff_held_medication_stays_pending_and_its_bin_is_not_ready():
    held = _order("NIGHT-HOLD", route="PO", room=7015, unit="SICU", due_time=NOW.replace(hour=21, minute=0))
    bin_seven = Bin(7)
    bin_seven.add_medication(held)
    app = create_app([bin_seven], [held], clock=lambda: NOW.replace(hour=20, minute=0))

    status, board = _request(app, "GET", "/bins")
    assert status == "200 OK"
    assert _bin_state(board, 7)["ready_to_tube"] is False

    status, result = _request(app, "POST", "/bins/7/tube")
    assert status == "200 OK"
    assert result["tubed_order_numbers"] == []
    assert held.tubed is False
    assert bin_seven.get_pending_medications() == [held]


def test_route_and_stat_priority_use_the_existing_rule_scores_and_ordering():
    bins = [Bin(4), Bin(5), Bin(6), Bin(7), Bin("ED")]
    orders = [
        _order("STAT-PO", status="STAT", route="PO", room=4012, unit="4"),
        _order("ROUTINE-IV", route="IV", room=5012, unit="5"),
        _order("ROUTINE-SUBQ", route="SubQ", room=6012, unit="6"),
        _order("ROUTINE-INHALED", route="Inhaled", room=7012, unit="7"),
        _order("ROUTINE-TOPICAL", route="Topical", room=8012, unit="ED"),
    ]
    for bin_obj, order in zip(bins, orders):
        bin_obj.add_medication(order)

    evaluation = TubingEngine().evaluate(bins, NOW)

    assert evaluation.sorted_bin_numbers == (4, 5, 6, 7, "ED")
    assert evaluation.medication_priority_scores == {
        "STAT-PO": 110,
        "ROUTINE-IV": 30,
        "ROUTINE-SUBQ": 20,
        "ROUTINE-INHALED": 10,
        "ROUTINE-TOPICAL": 5,
    }


def test_get_bins_returns_actual_board_state_for_standard_and_unknown_bins():
    ready = _order("API-READY", room=7015, unit="SICU")
    unknown_order = _order("API-UNKNOWN", room=7016, unit="SICU")
    bin_seven, unknown = Bin(7), Bin(UNKNOWN_BIN)
    bin_seven.add_medication(ready)
    unknown.add_medication(unknown_order)

    status, payload = _request(create_app([bin_seven, unknown], [ready, unknown_order], clock=lambda: NOW), "GET", "/bins")

    assert status == "200 OK"
    assert {item["bin_number"] for item in payload["bins"]} == {str(bin_id) for bin_id in TUBING_BIN_LOCATIONS if bin_id != UNKNOWN_BIN}
    assert _bin_state(payload, 7)["medication_count"] == 1
    assert _bin_state(payload, 7)["ready_to_tube"] is True
    assert _bin_state(payload, 7)["priority_score"] > 0
    assert _bin_state(payload, 7)["medications"][0]["order_number"] == "API-READY"
    assert payload["unknown_bin"]["medication_count"] == 1


def test_get_one_bin_returns_current_state_and_invalid_id_returns_404():
    order = _order("ONE-BIN", room=7015, unit="SICU")
    app = create_app([Bin(7, pending_medications=[order])], [order], clock=lambda: NOW)

    status, payload = _request(app, "GET", "/bins/BIN_7")
    assert status == "200 OK"
    assert payload["bin"]["bin_id"] == "BIN_7"
    assert payload["bin"]["medications"][0]["order_number"] == "ONE-BIN"

    status, payload = _request(app, "GET", "/bins/not-a-bin")
    assert status == "404 Not Found"
    assert payload == {"error": "Bin not found"}


def test_post_tube_moves_transfers_and_tubes_only_currently_eligible_orders():
    source, destination = Bin("ED"), Bin(7)
    eligible = _order("POST-ELIGIBLE", room=8012, unit="ED")
    held = _order("POST-HELD", route="PO", room=8013, unit="ED", due_time=NOW.replace(hour=21, minute=0))
    _transfer(eligible)
    _transfer(held)
    source.add_medication(eligible)
    source.add_medication(held)
    app = create_app([source, destination], [eligible, held], clock=lambda: NOW.replace(hour=20, minute=0))

    status, payload = _request(app, "POST", "/bins/7/tube")

    assert status == "200 OK"
    assert payload["tubed_order_numbers"] == ["POST-ELIGIBLE"]
    assert eligible.tubed is True
    assert held.tubed is False
    assert source.get_pending_medications() == []
    assert destination.get_pending_medications() == [held]
    assert {transfer["order_number"] for transfer in payload["detected_transfers"]} == {"POST-HELD"}
    assert _bin_state(payload, 7)["medication_count"] == 1
