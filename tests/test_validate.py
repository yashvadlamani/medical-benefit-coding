from benefit_coding import validate
from benefit_coding.fields import BY_NAME, FIELDS


def item(field, status="value", **values):
    base = {"field": field, "kind": BY_NAME[field].kind, "status": status, "amount": None, "copay": None,
            "coinsurance_pct": None, "deductible_applies": None, "flag": None, "quote": "", "page": 1,
            "confidence": 0.95, "citation_valid": True, "needs_review": False}
    return {**base, **values}


def plan(**overrides):
    """A complete, consistent plan: every field priced and cited."""
    fields = {f.name: item(f.name, "no_charge", quote="No charge") for f in FIELDS}
    fields["deductible_individual_in"] = item("deductible_individual_in", amount=1500, quote="$1,500 individual")
    fields["deductible_family_in"] = item("deductible_family_in", amount=3000, quote="$3,000 family")
    fields["oop_max_individual_in"] = item("oop_max_individual_in", amount=5000, quote="$5,000 individual")
    fields["oop_max_family_in"] = item("oop_max_family_in", amount=10000, quote="$10,000 family")
    fields.update(overrides)
    extraction = {"doc_id": "TEST", "fields": list(fields.values())}
    coded = {"fields": [{"field": name, "status": "mapped", "reason": ""} for name in fields]}
    return extraction, coded


def test_reconcile_passes_when_figures_are_in_the_quote():
    assert validate.reconcile(item("specialist_visit", copay=40, quote="Specialist visit $40 copay")) == []
    assert validate.reconcile(item("imaging", coinsurance_pct=20, quote="20% coinsurance")) == []
    assert validate.reconcile(item("deductible_family_in", amount=3000, quote="$1,500 / $3,000 family")) == []


def test_reconcile_catches_a_value_that_differs_from_the_sbc():
    problems = validate.reconcile(item("specialist_visit", copay=65, quote="Specialist visit $40 copay"))
    assert problems == ["$65 copay does not appear in the cited SBC passage"]
    assert validate.reconcile(item("imaging", coinsurance_pct=30, quote="20% coinsurance, $30 max"))


def test_price_copay_without_deductible():
    cost, _ = validate.price(item("pcp_visit", copay=30, deductible_applies=False), 150, 1500, 5000)
    assert cost == 30


def test_price_coinsurance_after_deductible():
    # $2,000 ER claim: $1,500 deductible, then 20% of the remaining $500
    cost, why = validate.price(item("emergency_room", coinsurance_pct=20, deductible_applies=True), 2000, 1500, 5000)
    assert cost == 1600 and "deductible" in why


def test_price_is_capped_at_the_out_of_pocket_limit():
    cost, why = validate.price(item("inpatient_facility", coinsurance_pct=50, deductible_applies=True), 20000, 1500, 5000)
    assert cost == 5000 and "capped" in why


def test_price_no_charge_not_covered_and_missing():
    assert validate.price(item("preventive_care", "no_charge"), 200, 1500, 5000)[0] == 0
    assert validate.price(item("rx_tier4_specialty", "not_covered"), 4000, 1500, 5000)[0] == 4000
    assert validate.price(item("imaging", "not_found"), 1500, 1500, 5000)[0] is None


def test_clean_plan_is_not_blocked():
    result = validate.validate(*plan(), verdicts={})
    assert result["summary"] == {"failed": 0, "warnings": 0, "attention": 0, "blocked": False}
    assert len(result["test_claims"]) == 8


def test_wrong_value_blocks_the_plan_and_flags_the_field():
    extraction, coded = plan(specialist_visit=item("specialist_visit", copay=65, quote="Specialist visit $40 copay"))
    result = validate.validate(extraction, coded, verdicts={})
    assert result["summary"]["blocked"]
    assert result["fields"]["specialist_visit"]["attention"]
    assert [c["check"] for c in result["checks"]] == ["sbc_reconciliation"]


def test_judge_verdicts_become_checks():
    verdicts = {"pcp_visit": {"verdict": "not_supported", "reason": "Document says $25"},
                "imaging": {"verdict": "unclear", "reason": "Two tiers"}}
    result = validate.validate(*plan(), verdicts=verdicts)
    assert {(c["field"], c["status"]) for c in result["checks"]} == {("pcp_visit", "fail"), ("imaging", "warn")}
    assert result["summary"]["blocked"]


def test_inconsistent_accumulators_fail():
    extraction, coded = plan(oop_max_individual_in=item("oop_max_individual_in", amount=1000, quote="$1,000"))
    checks = validate.validate(extraction, coded, verdicts={})["checks"]
    assert any(c["check"] == "consistency" and c["field"] == "oop_max_individual_in" for c in checks)


def test_field_missing_from_the_document_needs_review():
    extraction, coded = plan(prior_auth_imaging=item("prior_auth_imaging", "not_found", needs_review=True))
    info = validate.validate(extraction, coded, verdicts={})["fields"]["prior_auth_imaging"]
    assert info["attention"] and info["reasons"] == ["Not stated in the document"]
