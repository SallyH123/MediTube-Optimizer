"""
priority_rules.py

Contains medication priority scoring logic.

Higher score means:
    - medication should be considered for tubing earlier
    - technician should prioritize this medication

This module does NOT decide whether to tube.
It only calculates priority.
"""

from pharmacy_tube_optimizer.config import PRIORITY as STATUS_PRIORITY
from pharmacy_tube_optimizer.config import ROUTE_MAPPING, ROUTE_PRIORITY


def normalize_route(route: str) -> str:
    """Convert route input into a standard format."""
    route = route.upper()

    return ROUTE_MAPPING.get(route, route)


def get_status_priority(status: str) -> int:
    """Return priority score based on medication status."""
    status = status.upper()
    return STATUS_PRIORITY.get(status, 0)


def get_route_priority(route: str) -> int:
    """Return priority score based on medication route."""
    route = normalize_route(route)
    return ROUTE_PRIORITY.get(route, 0)


def get_medication_priority(status: str, route: str) -> int:
    """Calculate a medication priority score using status + route."""
    status_score = get_status_priority(status)
    route_score = get_route_priority(route)
    return status_score + route_score


def calculate_bin_priority_score(medications: list[dict]) -> float:
    """Calculate a bin-level priority score using the top medication and supporting meds."""
    if not medications:
        return 0.0

    highest_score = max(get_medication_priority(m["status"], m["route"]) for m in medications)
    additional_contribution = sum(get_medication_priority(m["status"], m["route"]) for m in medications) * 0.5

    return round(highest_score + additional_contribution, 2)


def rank_bins_for_tubing(bins: list[dict]) -> list[dict]:
    """Return bins sorted by highest priority score first."""
    return sorted(bins, key=lambda bin_item: calculate_bin_priority_score(bin_item["medications"]), reverse=True)
