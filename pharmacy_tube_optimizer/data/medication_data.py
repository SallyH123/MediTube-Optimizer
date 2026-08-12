from collections.abc import Iterable
from datetime import datetime, timedelta
from random import Random

from pharmacy_tube_optimizer.models.bin import Bin
from pharmacy_tube_optimizer.models.medication_order import MedicationOrder
from pharmacy_tube_optimizer.config import (
    ROOM_PREFIX_BIN_MAP,
    ROUTE_MAPPING,
    ROUTE_PRIORITY,
    TUBING_BIN_LOCATIONS,
    UNKNOWN_BIN,
)


TUBING_BIN_OPTIONS = tuple(bin_number for bin_number in TUBING_BIN_LOCATIONS if bin_number != UNKNOWN_BIN)
CLINICAL_UNITS = ("ED", "PERIOP", "CVICU", "SICU", "MICU")

# A focused 20-medication formulary covering common hospital tubing scenarios.
HOSPITAL_MEDICATION_POOL = (
    "Acetaminophen", "Albuterol", "Amlodipine", "Atorvastatin", "Cefepime",
    "Ceftriaxone", "Dexamethasone", "Enoxaparin", "Furosemide", "Heparin",
    "Hydromorphone", "Insulin Lispro", "Labetalol", "Levetiracetam", "Magnesium Sulfate",
    "Metoprolol", "Ondansetron", "Pantoprazole", "Piperacillin-Tazobactam", "Vancomycin",
)
# Demo orders start pending so every generated order is placed in an original
# bin and can be shown throughout the transfer-and-tubing workflow.
ORDER_STATUSES = ("Routine", "Routine", "Routine", "Routine", "STAT")


def generate_random_bin_number(rng: Random | None = None) -> int | str:
    """Return a random numeric bin or clinical-area label."""
    return (rng or Random()).choice(TUBING_BIN_OPTIONS)


def generate_random_room_number(bin_number: int | str | None = None, rng: Random | None = None) -> int:
    """Return a four-digit room that maps to the supplied physical bin."""
    randomizer = rng or Random()
    prefixes_by_bin = {}
    for prefix, mapped_bin in ROOM_PREFIX_BIN_MAP.items():
        prefixes_by_bin.setdefault(mapped_bin, []).append(prefix)
    prefix = randomizer.choice(prefixes_by_bin.get(bin_number, tuple(ROOM_PREFIX_BIN_MAP)))
    return int(f"{prefix}{randomizer.randint(0, 999):03d}")


def generate_random_order_id(rng: Random | None = None) -> str:
    """Return a five-digit order ID."""
    return f"{(rng or Random()).randint(10000, 99999)}"


def generate_random_route(rng: Random | None = None) -> str:
    """Return a route code from ``ROUTE_MAPPING``."""
    return (rng or Random()).choice(tuple(ROUTE_MAPPING.values()))


def generate_random_medication(rng: Random | None = None) -> str:
    """Return one medication from the 20-medication hospital pool."""
    return (rng or Random()).choice(HOSPITAL_MEDICATION_POOL)


def generate_random_status(rng: Random | None = None) -> str:
    """Return a status weighted toward pending routine orders."""
    return (rng or Random()).choice(ORDER_STATUSES)


def generate_random_due_time(reference_time: datetime | None = None, rng: Random | None = None) -> datetime:
    """Return a due time from now through 360 minutes after the reference time."""
    reference = reference_time or datetime.now()
    return reference + timedelta(minutes=(rng or Random()).randint(0, 360))


def generate_random_medication_orders(
    count: int = 10, *, seed: int | None = None, reference_time: datetime | None = None
) -> list[MedicationOrder]:
    """Generate reproducible model-valid orders for pytest fixtures and demos."""
    if not 0 <= count <= 90_000:
        raise ValueError("count must be between 0 and 90,000")

    randomizer = Random(seed)
    orders: list[MedicationOrder] = []
    used_order_ids: set[str] = set()
    while len(orders) < count:
        order_id = generate_random_order_id(randomizer)
        if order_id in used_order_ids:
            continue
        used_order_ids.add(order_id)
        bin_label = generate_random_bin_number(randomizer)
        unit = str(bin_label)
        orders.append(MedicationOrder(
            order_id=order_id,
            medication=generate_random_medication(randomizer),
            route=generate_random_route(randomizer),
            due_time=generate_random_due_time(reference_time, randomizer),
            status=generate_random_status(randomizer),
            room=generate_random_room_number(bin_label, randomizer),
            unit=unit,
            current_bin=bin_label,
        ))

    return orders

def generate_medication_orders() -> list[MedicationOrder]:
    """Create valid orders covering routine, STAT, and transfer workflows."""
    transferred_order = MedicationOrder(
        order_id="TRANSFER-7-TO-8",
        medication="Heparin",
        route="IV",
        due_time=datetime(2026, 8, 2, 10, 30),
        status="Routine",
        room=7012,
        unit="SICU",
    )
    transferred_order.update_location(room=8012, unit="MICU")

    return [
        MedicationOrder(
            order_id="ROUTINE-IV-8",
            medication="Cefepime",
            route="IV",
            due_time=datetime(2026, 8, 2, 10, 0),
            status="Routine",
            room=8012,
            unit="MICU",
        ),
        MedicationOrder(
            order_id="STAT-7",
            medication="Vancomycin",
            route="IV",
            due_time=datetime(2026, 8, 2, 9, 45),
            status="STAT",
            room=7015,
            unit="SICU",
        ),
        MedicationOrder(
            order_id="ROUTINE-PO-6",
            medication="Senna",
            route="PO",
            due_time=datetime(2026, 8, 2, 10, 30),
            status="Routine",
            room=6015,
            unit="CVICU",
        ),
        transferred_order,
    ]


def _has_valid_bin_placement(order: MedicationOrder) -> bool:
    """Return whether an order has complete, configuration-valid bin data.

    ``UNKNOWN`` is reserved for pending orders that cannot be safely sent to a
    clinical bin: missing placement fields, unsupported route/status, an
    invalid room, or inconsistent room/unit/bin values.
    """
    if not all((order.order_id, order.medication, order.route, order.due_time, order.status, order.room, order.unit)):
        return False
    if order.status.upper() not in {"ROUTINE", "STAT"}:
        return False
    if order.route.upper() not in ROUTE_PRIORITY:
        return False
    if not isinstance(order.room, int) or len(str(order.room)) != 4:
        return False

    expected_bin = ROOM_PREFIX_BIN_MAP.get(str(order.room)[0])
    if expected_bin is None or order.current_bin != expected_bin:
        return False
    return str(order.unit).upper() == str(expected_bin).upper()


def generate_bins(orders: Iterable[MedicationOrder] | None = None) -> list[Bin]:
    """Create the mock tubing bins and optionally place supplied orders in them.

    A transferred order is intentionally seeded in its previous bin. Transfer
    rules then move it to the bin associated with its current location.
    """
    bins = [Bin(bin_number) for bin_number in TUBING_BIN_LOCATIONS]
    bins_by_number = {bin_obj.bin_number: bin_obj for bin_obj in bins}

    for order in orders or []:
        if order.status.upper() in {"TUBED", "COMPLETED", "DONE"}:
            continue
        bin_number = order.current_bin
        destination_bin = (
            bins_by_number[bin_number]
            if _has_valid_bin_placement(order) and bin_number in bins_by_number
            else bins_by_number[UNKNOWN_BIN]
        )
        destination_bin.add_medication(order)

    return bins
