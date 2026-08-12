from collections.abc import Mapping
from random import Random

from pharmacy_tube_optimizer.config import ROOM_PREFIX_BIN_MAP
from pharmacy_tube_optimizer.data.medication_data import generate_random_room_number
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder

# These records mirror the deterministic medication fixtures:
# TRANSFER-7-TO-8 moves from room 7012/Bin 7 to room 8012/Bin 8.
PATIENT_TRANSFER_RECORDS: Mapping[str, tuple[str, str]] = {
    "P001": ("7012", "8012"),
    "P002": ("7015", "7015"),
    "P003": ("6015", "6015"),
}


def generate_patient_location_data() -> Mapping[str, str]:
    """Return the current rooms for the deterministic medication fixtures."""
    return {patient_id: current_room for patient_id, (_, current_room) in PATIENT_TRANSFER_RECORDS.items()}


def generate_patient_transfers() -> list[tuple[str, str]]:
    """Return ``(original_room, current_room)`` pairs for transfer-rule checks."""
    return list(PATIENT_TRANSFER_RECORDS.values())


def generate_random_patient_transfer(
    orders: list[MedicationOrder], *, rng: Random | None = None
) -> tuple[MedicationOrder, int, int | str]:
    """Transfer one already-generated order to a new random room and bin."""
    transferable_orders = [
        order for order in orders if order.status.upper() not in {"TUBED", "COMPLETED", "DONE"}
    ]
    if not transferable_orders:
        raise ValueError("Cannot generate a transfer without a pending medication order.")

    randomizer = rng or Random()
    order = randomizer.choice(transferable_orders)
    available_bins = tuple(ROOM_PREFIX_BIN_MAP.values())
    destination_bin = randomizer.choice(
        tuple(bin_number for bin_number in available_bins if bin_number != order.current_bin)
    )
    destination_room = generate_random_room_number(destination_bin, randomizer)
    order.update_location(room=destination_room, unit=str(destination_bin))
    return order, destination_room, destination_bin
