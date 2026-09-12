from __future__ import annotations

"""Input validation helpers for medication-order domain objects."""

from typing import Any


def validate_medication_order(order: Any) -> None:
    """Raise ``ValueError`` when a medication order lacks required fields."""
    if not order.order_id:
        raise ValueError("Order ID is required")
    if not order.medication:
        raise ValueError("Medication is required")
    if not order.route:
        raise ValueError("Route is required")


def validate_room_number(room: int | None) -> bool:
    """Return whether a room number is absent or a supported positive integer."""
    if room is None:
        return False
    return isinstance(room, int) and room > 0
