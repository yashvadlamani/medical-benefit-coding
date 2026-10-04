import pytest

from benefit_coding import mapping


@pytest.fixture(scope="module")
def library():
    return mapping.read_seed()  # the seed file, so tests make no network calls


def item(field, status="value", **values):
    base = {"field": field, "status": status, "amount": None, "copay": None, "coinsurance_pct": None,
            "deductible_applies": None, "flag": None, "quote": "q", "page": 1, "confidence": 0.95,
            "citation_valid": True, "needs_review": False}
    return {**base, **values}


def test_copay_maps_to_code(library):
    result = mapping.map_field(item("pcp_visit", copay=30.0, deductible_applies=False), library)
    assert result["status"] == "mapped" and result["codes"] == ["PCP-CP0030"]
    assert result["parameters"] == {"deductible_applies": False}
    assert result["needs_review"] is False


def test_copay_plus_coinsurance_maps_to_two_codes(library):
    result = mapping.map_field(item("emergency_room", copay=250, coinsurance_pct=20), library)
    assert result["codes"] == ["ER-CP0250", "ER-CI020"]


def test_amount_carries_dollar_value_as_parameter(library):
    result = mapping.map_field(item("deductible_individual_in", amount=1500), library)
    assert result["codes"] == ["ACC-DED-IND-INN"] and result["parameters"]["amount"] == 1500


def test_not_applicable_amount(library):
    result = mapping.map_field(item("oop_max_family_oon", status="not_applicable"), library)
    assert result["codes"] == ["ACC-OOP-FAM-OON-NA"]


def test_no_charge_and_not_covered(library):
    assert mapping.map_field(item("preventive_care", status="no_charge"), library)["codes"] == ["PRV-NC"]
    assert mapping.map_field(item("rx_tier4_specialty", status="not_covered"), library)["codes"] == ["RX4-NCOV"]


def test_unusual_value_is_unmapped_with_nearest_suggestions(library):
    result = mapping.map_field(item("specialist_visit", copay=37), library)
    assert result["status"] == "unmapped" and result["codes"] == []
    assert set(result["suggestions"]) == {"SPC-CP0035", "SPC-CP0040"}
    assert result["needs_review"] is True


def test_missing_value_goes_to_review(library):
    result = mapping.map_field(item("prior_auth_imaging", status="not_found", needs_review=True), library)
    assert result["status"] == "no_value" and result["needs_review"] is True


def test_flag(library):
    assert mapping.map_field(item("prior_auth_inpatient", flag=True), library)["codes"] == ["PA-IP-Y"]


def test_low_confidence_extraction_is_reviewed_even_when_mapped(library):
    result = mapping.map_field(item("pcp_visit", copay=30, needs_review=True), library)
    assert result["status"] == "mapped" and result["needs_review"] is True
