from pharmacy_tube_optimizer.rules.transfer_rules import (
    check_transfer_before_tubing,
    get_bin_from_room,
    get_current_patient_location,
    get_destination_bin,
    get_unit_from_room,
    has_patient_transferred,
    normalize_room,
)


def test_normalize_room_and_unit_from_room():
    assert normalize_room(" 8012 ") == "8012"
    assert get_unit_from_room("8012") == "ED"
    assert get_unit_from_room("ER") == "ER"


def test_room_prefixes_map_to_requested_physical_bins():
    assert get_bin_from_room("1012") == "CVICU"
    assert get_bin_from_room("2012") == "SICU"
    assert get_bin_from_room("3012") == "MICU"
    assert get_bin_from_room("4012") == "4"
    assert get_bin_from_room("7012") == "7"
    assert get_bin_from_room("8012") == "ED"
    assert get_bin_from_room("9012") == "PERIOP"


def test_transfer_detection_and_bin_selection():
    assert has_patient_transferred("8012", "7015") is True
    assert has_patient_transferred("8012", "8012") is False
    assert get_bin_from_room("7015") == "7"
    assert get_destination_bin("5012") == "5"


def test_location_lookup_and_transfer_summary():
    location_data = {"P001": "7015", "P002": "8012"}
    assert get_current_patient_location("P001", location_data) == "7015"

    result = check_transfer_before_tubing("8012", "7015")
    assert result["transferred"] is True
    assert result["original_bin"] == "ED"
    assert result["destination_bin"] == "7"
