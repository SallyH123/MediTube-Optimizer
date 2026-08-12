from __future__ import annotations

from typing import Any


def validate_medication_order(order: Any) -> None:
    if not order.order_id:
        raise ValueError("Order ID is required")
    if not order.medication:
        raise ValueError("Medication is required")
    if not order.route:
        raise ValueError("Route is required")


def validate_room_number(room: int | None) -> bool:
    if room is None:
        return False
    return isinstance(room, int) and room > 0
