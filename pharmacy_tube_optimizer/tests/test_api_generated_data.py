from datetime import datetime
from io import BytesIO
import json

from pharmacy_tube_optimizer.api.app import create_app
from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS


def test_default_api_uses_the_random_backend_data_generator():
    now = datetime(2026, 8, 2, 10, 0)

    app = create_app(clock=lambda: now)

    assert len(app.medication_service.orders) == 10
    assert {bin_obj.bin_number for bin_obj in app.bins} == set(TUBING_BIN_LOCATIONS)
    assert all(now <= order.due_time <= now.replace(hour=16) for order in app.medication_service.orders)


def test_default_api_reports_the_generated_patient_transfer():
    now = datetime(2026, 8, 2, 10, 0)
    app = create_app(clock=lambda: now)
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status

    body = b"".join(app({"REQUEST_METHOD": "GET", "PATH_INFO": "/bins", "wsgi.input": BytesIO()}, start_response))
    payload = json.loads(body)

    assert captured["status"] == "200 OK"
    assert len(payload["detected_transfers"]) == 1
    assert payload["detected_transfers"][0]["old_room"] != payload["detected_transfers"][0]["new_room"]
