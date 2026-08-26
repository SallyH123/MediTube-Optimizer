"""
transfer_rules.py

Handles patient transfer detection and destination bin assignment.

Important design principle:
    A medication may remain in its original pharmacy bin for hours.
    We do NOT continuously move medications between bins when a patient
    transfers.

Instead, transfer information is checked immediately before tubing.

This module is responsible for:
    - determining the patient's current location
    - detecting whether the patient has transferred
    - determining the correct destination bin

This module does NOT:
    - decide whether a medication should be tubed
    - apply cutoff rules
    - calculate medication priority
    - decide whether a medication should remain in its source bin before tubing
"""

from __future__ import annotations

from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.config import ROOM_PREFIX_BIN_MAP, UNKNOWN_BIN


def normalize_room(room: str) -> str:
    """Normalize a room number into a standard format."""
    return str(room).strip().upper()


def get_unit_from_room(room: str) -> str:
    """Determine the unit/bin from a room number or special unit."""
    room = normalize_room(room)

    if not room:
        raise ValueError("Room cannot be empty.")

    if room == "ER":
        return "ER"
    if room == "ED":
        return "ED"
    if room == "PERIOP":
        return "PERIOP"
    # The board always has a separate UNKNOWN bin.  A location which does not
    # map safely to a configured clinical destination must be held there,
    # rather than aborting the final transfer check or guessing a standard bin.
    return str(ROOM_PREFIX_BIN_MAP.get(room[0], UNKNOWN_BIN))


def get_bin_from_room(room: str) -> str:
    """Determine the tubing bin associated with a room."""
    return get_unit_from_room(room)


def has_patient_transferred(original_room: str, current_room: str) -> bool:
    """Return True when the patient has moved to a different room."""
    return normalize_room(original_room) != normalize_room(current_room)


def get_current_patient_location(patient_id: str, location_data: dict) -> str:
    """Retrieve the patient's current room from transfer/location data."""
    patient_id = str(patient_id).strip()

    if patient_id not in location_data:
        raise ValueError(f"Current location not found for patient {patient_id}.")

    return normalize_room(location_data[patient_id])


def get_destination_bin(current_room: str) -> str:
    """Determine the correct tubing bin based on the patient's current room."""
    return get_bin_from_room(current_room)


def check_transfer_before_tubing(original_room: str, current_room: str) -> dict:
    """Check the patient's current location immediately before tubing."""
    original_room = normalize_room(original_room)
    current_room = normalize_room(current_room)

    transferred = has_patient_transferred(original_room, current_room)

    return {
        "transferred": transferred,
        "original_room": original_room,
        "current_room": current_room,
        "original_bin": get_bin_from_room(original_room),
        "destination_bin": get_destination_bin(current_room),
    }


def get_transfer_details(order: MedicationOrder) -> dict | None:
    """Return transfer details for an order when both locations are known."""
    original_room = get_previous_room(order)
    current_room = get_current_room(order)
    if original_room is None or current_room is None:
        return None
    return check_transfer_before_tubing(original_room, current_room)


def get_destination_bin_number(transfer_details: dict) -> int | str | None:
    """Return a numeric or named destination-bin identifier."""
    destination_bin = transfer_details["destination_bin"]
    if isinstance(destination_bin, int):
        return destination_bin
    if isinstance(destination_bin, str):
        stripped = destination_bin.strip()
        if stripped.isdigit():
            return int(stripped)
        if stripped and stripped[0].isdigit():
            return int(stripped[0])
        if stripped:
            return stripped.upper()
    return None


def get_previous_room(order: MedicationOrder) -> str | None:
    """Return the patient's original room when available."""
    if order.previous_location is not None:
        return str(order.previous_location.room)
    if order.location is not None:
        return str(order.location.room)
    return None


def get_current_room(order: MedicationOrder) -> str | None:
    """Return the patient's current room when available."""
    if order.location is not None:
        return str(order.location.room)
    return order.room if order.room is not None else None
