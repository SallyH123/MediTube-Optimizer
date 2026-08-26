from datetime import datetime

from pharmacy_tube_optimizer.api.app import create_app
from pharmacy_tube_optimizer.config import TUBING_BIN_LOCATIONS


def test_default_api_uses_the_random_backend_data_generator():
    now = datetime(2026, 8, 2, 10, 0)

    app = create_app(clock=lambda: now)

    assert len(app.medication_service.orders) == 10
    assert {bin_obj.bin_number for bin_obj in app.bins} == set(TUBING_BIN_LOCATIONS)
    assert all(now <= order.due_time <= now.replace(hour=16) for order in app.medication_service.orders)
