"""Step 4. Validate a coded plan: reconcile it with the SBC, run consistency rules, and price test claims.

A plan with any failed check is blocked: it cannot be approved until a reviewer has decided every flagged field.
"""
import re

from .fields import AMOUNT, BY_NAME, COST_SHARE, describe

# ACA maximum out-of-pocket limits for plan year 2026 (self-only, family). Reported as a warning, not a failure.
ACA_OOP_LIMIT = {"oop_max_individual_in": 10600, "oop_max_family_in": 21200}

# (scenario, field that prices it, allowed amount for the claim). The amounts are illustrative round numbers.
SCENARIOS = [
    ("Preventive visit", "preventive_care", 200),
    ("Primary care visit", "pcp_visit", 150),
    ("Specialist visit", "specialist_visit", 250),
    ("Emergency room visit", "emergency_room", 2000),
    ("MRI", "imaging", 1500),
    ("Hospital stay", "inpatient_facility", 20000),
    ("Generic drug, 30 days", "rx_tier1_generic", 20),
    ("Specialty drug, 30 days", "rx_tier4_specialty", 4000),
]


def _numbers(text, suffix=""):
    """Dollar or percent figures in a passage: _numbers('$1,500 then 20%') -> {1500.0}; with '%' -> {20.0}."""
    pattern = r"(\d[\d,]*(?:\.\d+)?)\s*%" if suffix == "%" else r"\$\s*(\d[\d,]*(?:\.\d+)?)"
    return {float(n.replace(",", "")) for n in re.findall(pattern, text)}


def reconcile(item):
    """Check that the coded figures appear in the passage cited from the SBC. Returns a list of problems."""
    if item["status"] != "value":
        return []
    quote, problems = item["quote"], []
    if item["kind"] == AMOUNT and float(item["amount"]) not in _numbers(quote):
        problems.append(f"${item['amount']:,.0f} does not appear in the cited SBC passage")
    if item["kind"] == COST_SHARE:
        if item["copay"] and float(item["copay"]) not in _numbers(quote):
            problems.append(f"${item['copay']:,.0f} copay does not appear in the cited SBC passage")
        if item["coinsurance_pct"] and float(item["coinsurance_pct"]) not in _numbers(quote, "%"):
            problems.append(f"{item['coinsurance_pct']:g}% coinsurance does not appear in the cited SBC passage")
    return problems


def price(item, allowed, deductible, oop_max):
    """Member cost for one claim, treated as the first claim of the year. Returns (cost or None, explanation)."""
    if item["status"] == "no_charge":
        return 0.0, "No charge"
    if item["status"] == "not_covered":
        return float(allowed), "Not covered: member pays the full allowed amount"
    if item["status"] != "value":
        return None, "Cannot price: the benefit was not found in the document"

    cost, remaining, steps = 0.0, float(allowed), []
    if item["deductible_applies"]:
        if deductible is None:
            return None, "Cannot price: the deductible applies but no deductible was coded"
        paid = min(remaining, deductible)
        cost, remaining = cost + paid, remaining - paid
        steps.append(f"${paid:,.0f} toward the ${deductible:,.0f} deductible")
    if item["copay"]:
        paid = min(remaining, float(item["copay"]))
        cost, remaining = cost + paid, remaining - paid
        steps.append(f"${paid:,.0f} copay")
    if item["coinsurance_pct"]:
        paid = remaining * float(item["coinsurance_pct"]) / 100
        cost += paid
        steps.append(f"{item['coinsurance_pct']:g}% of the remaining ${remaining:,.0f}")
    if oop_max is not None and cost > oop_max:
        cost = oop_max
        steps.append(f"capped at the ${oop_max:,.0f} out-of-pocket limit")
    return round(cost, 2), "; ".join(steps) or "No cost sharing coded"


def test_claims(fields):
    """Price the standard scenarios from the extracted values."""
    def amount(name):
        item = fields[name]
        return float(item["amount"]) if item["status"] == "value" else None

    deductible, oop_max = amount("deductible_individual_in"), amount("oop_max_individual_in")
    claims = []
    for scenario, field, allowed in SCENARIOS:
        cost, explanation = price(fields[field], allowed, deductible, oop_max)
        claims.append({"scenario": scenario, "field": field, "allowed": allowed, "member_cost": cost,
                       "plan_pays": None if cost is None else round(allowed - cost, 2),
                       "explanation": explanation, "status": "fail" if cost is None else "pass"})
    return claims


def _consistency(fields):
    """Rules that hold for any plan design, whatever the document says."""
    def amount(name):
        item = fields[name]
        return float(item["amount"]) if item["status"] == "value" else None

    checks = []
    pairs = [("deductible_family_in", "deductible_individual_in", "Family deductible is below the individual deductible"),
             ("oop_max_family_in", "oop_max_individual_in", "Family out-of-pocket limit is below the individual limit"),
             ("oop_max_individual_in", "deductible_individual_in", "Out-of-pocket limit is below the deductible"),
             ("oop_max_family_in", "deductible_family_in", "Family out-of-pocket limit is below the family deductible")]
    for larger, smaller, message in pairs:
        if amount(larger) is not None and amount(smaller) is not None and amount(larger) < amount(smaller):
            checks.append({"check": "consistency", "field": larger, "status": "fail",
                           "detail": f"{message} (${amount(larger):,.0f} vs ${amount(smaller):,.0f})"})
    for name, limit in ACA_OOP_LIMIT.items():
        if amount(name) is not None and amount(name) > limit:
            checks.append({"check": "aca_limit", "field": name, "status": "warn",
                           "detail": f"${amount(name):,.0f} is above the 2026 ACA limit of ${limit:,.0f}"})
    return checks


def validate(extraction, coded, verdicts):
    """Run every check for one plan. verdicts is {field: {"verdict", "reason"}} from the LLM judge."""
    fields = {item["field"]: item for item in extraction["fields"]}
    mapped = {item["field"]: item for item in coded["fields"]}
    checks = _consistency(fields)

    for name, item in fields.items():
        for problem in reconcile(item):
            checks.append({"check": "sbc_reconciliation", "field": name, "status": "fail", "detail": problem})
        if item["status"] != "not_found" and not item["citation_valid"]:
            checks.append({"check": "citation", "field": name, "status": "fail",
                           "detail": "The cited passage was not found in the document"})
        verdict = verdicts.get(name)
        if verdict and verdict["verdict"] == "not_supported":
            checks.append({"check": "judge", "field": name, "status": "fail", "detail": verdict["reason"]})
        elif verdict and verdict["verdict"] == "unclear":
            checks.append({"check": "judge", "field": name, "status": "warn", "detail": verdict["reason"]})
        if mapped[name]["status"] == "unmapped":
            checks.append({"check": "code_mapping", "field": name, "status": "fail",
                           "detail": f"No system code: {mapped[name]['reason']}"})

    claims = test_claims(fields)
    for claim in claims:
        if claim["status"] == "fail":
            checks.append({"check": "test_claim", "field": claim["field"], "status": "fail",
                           "detail": f"{claim['scenario']}: {claim['explanation']}"})

    # one record per field for the review screen: what the reviewer must look at, and why
    review = {}
    for name, item in fields.items():
        reasons = [c["detail"] for c in checks if c["field"] == name]
        if item["status"] == "not_found":
            reasons.append("Not stated in the document")
        elif item["needs_review"] and not reasons:
            reasons.append(f"Low extraction confidence ({item['confidence']:.2f})")
        review[name] = {"attention": bool(reasons), "reasons": reasons, "value": describe(item),
                        "description": BY_NAME[name].description, "judge": verdicts.get(name)}

    failed = sum(c["status"] == "fail" for c in checks)
    return {
        "doc_id": extraction["doc_id"],
        "checks": checks,
        "test_claims": claims,
        "fields": review,
        "summary": {"failed": failed, "warnings": sum(c["status"] == "warn" for c in checks),
                    "attention": sum(r["attention"] for r in review.values()), "blocked": failed > 0},
    }
