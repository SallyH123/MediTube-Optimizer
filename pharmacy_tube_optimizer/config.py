"""
config.py

Central configuration file for Meditube Optimizer.

Contains:
- Unit definitions
- Tubing rules
- Cutoff times
- Medication priorities
- Grace periods
"""

from datetime import time


# ==========================================
# Units
# ==========================================

ER_UNITS = {"ED", "ER", "PERIOP"}

STANDARD_UNITS = {"CVICU", "SICU", "MICU", *map(str, range(1, 10))}


# ==========================================
# Tubing windows
# ==========================================

STANDARD_ROUTINE_WINDOW_HOURS = 5
ER_ROUTINE_WINDOW_HOURS = 1
BIN_REVIEW_WINDOW_HOURS = 1


# ==========================================
# Day / night cutoff rules
# ==========================================

DAY_CUTOFF_CURRENT_TIME = time(8, 30)
DAY_HOLD_DUE_TIME = time(9, 0)

NIGHT_CUTOFF_CURRENT_TIME = time(20, 30)
NIGHT_HOLD_DUE_TIME = time(21, 0)


# ==========================================
# Medication priorities
# Higher score = higher priority
# ==========================================

PRIORITY = {
    "STAT": 100,
    "ROUTINE": 0,
}


# ==========================================
# Grace periods
# ==========================================

IV_GRACE_MINUTES = 15

ORAL_GRACE_MINUTES = 30


# ==========================================
# Transfer checking
# ==========================================

CHECK_TRANSFER_BEFORE_TUBE = True


# ==========================================
# Logging
# ==========================================

LOG_FILE = "logs/app.log"


# ==========================================
# Bin mapping
# ==========================================

BIN_PREFIX_MAP = {
    "1": "BIN_CVICU",
    "2": "BIN_SICU",
    "3": "BIN_MICU",
    "4": "BIN_4",
    "5": "BIN_5",
    "6": "BIN_6",
    "7": "BIN_7",
    "8": "BIN_ED",
    "9": "BIN_PERIOP",
    "ED": "BIN_ED",
    "PERIOP": "BIN_PERIOP",
    "CVICU": "BIN_CVICU",
    "SICU": "BIN_SICU",
    "MICU": "BIN_MICU",
}


# ==========================================
# Status
# ==========================================

STATUS_ROUTINE = "ROUTINE"

STATUS_STAT = "STAT"


# ==========================================
# Routes
# ==========================================

ROUTE_IV = "IV"

ROUTE_PO = "PO"

# Canonical route values and aliases used by ``rules.priority_rules`` and the
# random medication data generator. Every canonical value has a route score.
ROUTE_MAPPING = {
    "ORAL": "PO",
    "PER OS": "PO",
    "INTRAVENOUS": "IV",
    "SUBCUTANEOUS": "SUBQ",
    "SC": "SUBQ",
    "SQ": "SUBQ",
    "INTRAMUSCULAR": "IM",
    "INHALATION": "INHALER",
    "INHALED": "INHALER",
    "TOPICAL": "TOPICAL",
    "TRANSDERMAL": "TOPICAL",
}

ROOM_PREFIX_BIN_MAP = {
    "1": "CVICU", "2": "SICU", "3": "MICU", "4": 4, "5": 5,
    "6": 6, "7": 7, "8": "ED", "9": "PERIOP",
}

UNKNOWN_BIN = "UNKNOWN"

ROUTE_PRIORITY = {
    "IV": 30,
    "SUBQ": 20,
    "IM": 20,
    "INHALER": 10,
    "PO": 10,
    "TOPICAL": 5,
}

# Physical tubing bins. These bins are created even when they currently hold
# no medications, so transfer destinations always have a valid queue.
TUBING_BIN_LOCATIONS: tuple[int | str, ...] = (4, 5, 6, 7) + (
    "ED",
    "PERIOP",
    "CVICU",
    "SICU",
    "MICU",
    UNKNOWN_BIN,
)


# ==========================================
# Helper accessors
# ==========================================

def get_system_rules() -> dict:
    """Return the main tubing configuration values."""
    return {
        "er_units": ER_UNITS,
        "standard_units": STANDARD_UNITS,
        "standard_routine_window_hours": STANDARD_ROUTINE_WINDOW_HOURS,
        "er_routine_window_hours": ER_ROUTINE_WINDOW_HOURS,
        "bin_review_window_hours": BIN_REVIEW_WINDOW_HOURS,
        "day_cutoff_current_time": DAY_CUTOFF_CURRENT_TIME,
        "day_hold_due_time": DAY_HOLD_DUE_TIME,
        "night_cutoff_current_time": NIGHT_CUTOFF_CURRENT_TIME,
        "night_hold_due_time": NIGHT_HOLD_DUE_TIME,
        "priority": PRIORITY,
        "iv_grace_minutes": IV_GRACE_MINUTES,
        "oral_grace_minutes": ORAL_GRACE_MINUTES,
        "check_transfer_before_tube": CHECK_TRANSFER_BEFORE_TUBE,
        "log_file": LOG_FILE,
        "bin_prefix_map": BIN_PREFIX_MAP,
        "room_prefix_bin_map": ROOM_PREFIX_BIN_MAP,
        "unknown_bin": UNKNOWN_BIN,
        "status_routine": STATUS_ROUTINE,
        "status_stat": STATUS_STAT,
        "route_iv": ROUTE_IV,
        "route_po": ROUTE_PO,
        "route_mapping": ROUTE_MAPPING,
        "route_priority": ROUTE_PRIORITY,
        "tubing_bin_locations": TUBING_BIN_LOCATIONS,
    }


def get_priority_rules() -> dict:
    """Return medication priority settings."""
    return PRIORITY


def get_cutoff_rules() -> dict:
    """Return day and night cutoff settings."""
    return {
        "day_cutoff": DAY_CUTOFF_CURRENT_TIME,
        "day_hold_due": DAY_HOLD_DUE_TIME,
        "night_cutoff": NIGHT_CUTOFF_CURRENT_TIME,
        "night_hold_due": NIGHT_HOLD_DUE_TIME,
    }


def get_grace_period_rules() -> dict:
    """Return grace period settings."""
    return {
        "iv_grace_minutes": IV_GRACE_MINUTES,
        "oral_grace_minutes": ORAL_GRACE_MINUTES,
    }
