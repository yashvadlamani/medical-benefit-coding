"""Score extracted fields against the values published in the CMS Exchange Public Use Files."""
import csv
import json
import re
from collections import defaultdict

from . import config
from .fields import AMOUNT, COST_SHARE, FIELDS

GOLDEN = config.DATA / "golden" / "2026"

# field -> BenefitName in the Benefits and Cost Sharing file
BENEFIT_NAMES = {
    "pcp_visit": "Primary Care Visit to Treat an Injury or Illness",
    "specialist_visit": "Specialist Visit",
    "preventive_care": "Preventive Care/Screening/Immunization",
    "emergency_room": "Emergency Room Services",
    "urgent_care": "Urgent Care Centers or Facilities",
    "inpatient_facility": "Inpatient Hospital Services (e.g., Hospital Stay)",
    "outpatient_surgery_facility": "Outpatient Facility Fee (e.g., Ambulatory Surgery Center)",
    "imaging": "Imaging (CT/PET Scans, MRIs)",
    "rx_tier1_generic": "Generic Drugs",
    "rx_tier2_preferred_brand": "Preferred Brand Drugs",
    "rx_tier3_nonpreferred_brand": "Non-Preferred Brand Drugs",
    "rx_tier4_specialty": "Specialty Drugs",
}
# field -> column suffix in the Plan Attributes file (prefixed by MEHB or TEHB)
AMOUNT_COLUMNS = {
    "deductible_individual_in": "DedInnTier1Individual",
    "deductible_family_in": "DedInnTier1FamilyPerGroup",
    "deductible_individual_oon": "DedOutOfNetIndividual",
    "deductible_family_oon": "DedOutOfNetFamilyPerGroup",
    "oop_max_individual_in": "InnTier1IndividualMOOP",
    "oop_max_family_in": "InnTier1FamilyPerGroupMOOP",
    "oop_max_individual_oon": "OutOfNetIndividualMOOP",
    "oop_max_family_oon": "OutOfNetFamilyPerGroupMOOP",
}


def _dollars(text):
    """'$1,500 ' or '$3000 per group' -> 1500.0 / 3000.0; blank or 'not applicable' -> None."""
    match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", text or "")
    return float(match.group(1).replace(",", "")) if match else None


def _percent(text):
    match = re.search(r"([\d.]+)\s*%", text or "")
    return float(match.group(1)) if match else None


def golden_plan(plan_id):
    """Expected value per field for the plan's standard on-exchange variant."""
    variant = f"{plan_id}-01"
    with open(GOLDEN / "plan-attributes.csv", encoding="utf-8") as f:
        attributes = next(r for r in csv.DictReader(f) if r["PlanId"] == variant)
    with open(GOLDEN / "benefits-and-cost-sharing.csv", encoding="utf-8") as f:
        benefits = {r["BenefitName"]: r for r in csv.DictReader(f) if r["PlanId"] == variant}

    expected = {}
    for field, column in AMOUNT_COLUMNS.items():
        # plans with an integrated medical and drug accumulator report it under TEHB, others under MEHB
        is_deductible = column.startswith("Ded")
        integrated = attributes["MedicalDrugDeductiblesIntegrated" if is_deductible
                                else "MedicalDrugMaximumOutofPocketIntegrated"] == "Yes"
        value = _dollars(attributes[("TEHB" if integrated else "MEHB") + column])
        if value is None:
            value = _dollars(attributes[("MEHB" if integrated else "TEHB") + column])
        expected[field] = ("amount", value)
    for field, name in BENEFIT_NAMES.items():
        row = benefits.get(name)
        if row is None:
            continue
        if row["IsCovered"] != "Covered":
            expected[field] = ("not_covered",)
        else:
            expected[field] = ("cost_share", _dollars(row["CopayInnTier1"]) or 0.0, _percent(row["CoinsInnTier1"]) or 0.0)
    return expected


def actual_value(item):
    """Extracted field in the same shape as the golden value."""
    if item["kind"] == AMOUNT:
        return ("amount", float(item["amount"]) if item["status"] == "value" else None)
    if item["status"] == "not_covered":
        return ("not_covered",)
    return ("cost_share", float(item["copay"] or 0), float(item["coinsurance_pct"] or 0))


def score(plan_ids, complexity):
    """Compare every extracted plan with its golden values. Returns (rows, mismatches, citation stats)."""
    rows, mismatches = [], []
    cited = total_values = 0
    for plan_id in plan_ids:
        path = config.OUTPUT / "extracted" / f"{plan_id}.json"
        if not path.exists():
            continue
        extraction = json.loads(path.read_text(encoding="utf-8"))
        expected = golden_plan(plan_id)
        for item in extraction["fields"]:
            if item["status"] != "not_found":
                total_values += 1
                cited += item["citation_valid"]
            if item["field"] not in expected:
                continue
            want, got = expected[item["field"]], actual_value(item)
            correct = want == got
            rows.append({"plan": plan_id, "field": item["field"], "complexity": complexity[plan_id],
                         "correct": correct, "needs_review": item["needs_review"]})
            if not correct:
                mismatches.append({"plan": plan_id, "field": item["field"], "expected": want, "extracted": got,
                                   "quote": item["quote"], "confidence": item["confidence"]})
    return rows, mismatches, (cited, total_values)


def _pct(rows):
    return f"{100 * sum(r['correct'] for r in rows) / len(rows):.1f}%" if rows else "n/a"


def _show(value):
    if value[0] == "amount":
        return "not applicable" if value[1] is None else f"${value[1]:,.0f}"
    if value[0] == "not_covered":
        return "not covered"
    parts = ([f"${value[1]:,.0f} copay"] if value[1] else []) + ([f"{value[2]:g}%"] if value[2] else [])
    return " + ".join(parts) or "no charge"


def report(plan_ids, complexity):
    """Build the accuracy report as markdown."""
    rows, mismatches, (cited, total_values) = score(plan_ids, complexity)
    plans = sorted({r["plan"] for r in rows})
    by_field, by_plan = defaultdict(list), defaultdict(list)
    for r in rows:
        by_field[r["field"]].append(r)
        by_plan[r["plan"]].append(r)
    flagged_wrong = sum(1 for r in rows if not r["correct"] and r["needs_review"])
    wrong = sum(1 for r in rows if not r["correct"])

    out = ["# Extraction accuracy report", "",
           f"Scored {len(rows)} fields across {len(plans)} plans against the values published in the CMS Exchange "
           "Public Use Files (plan year 2026). The two prior-authorization flags have no published value and are "
           "not scored.", "",
           "## Summary", "", "| Measure | Result |", "| --- | --- |",
           f"| Field accuracy, all plans | {_pct(rows)} |",
           f"| Field accuracy, simple plans | {_pct([r for r in rows if r['complexity'] == 'simple'])} |",
           f"| Field accuracy, moderate plans | {_pct([r for r in rows if r['complexity'] == 'moderate'])} |",
           f"| Extracted values with a citation found in the document | {cited} of {total_values} |",
           f"| Plans with every scored field correct | {sum(all(r['correct'] for r in v) for v in by_plan.values())} of {len(plans)} |",
           f"| Wrong fields that were flagged for review | {flagged_wrong} of {wrong} |",
           "", "## Accuracy by field", "", "| Field | Correct | Accuracy |", "| --- | --- | --- |"]
    for f in FIELDS:
        if f.name in by_field:
            group = by_field[f.name]
            out.append(f"| {f.name} | {sum(r['correct'] for r in group)} of {len(group)} | {_pct(group)} |")
    out += ["", "## Accuracy by plan", "", "| Plan | Complexity | Correct | Accuracy |", "| --- | --- | --- | --- |"]
    for plan in plans:
        group = by_plan[plan]
        out.append(f"| {plan} | {complexity[plan]} | {sum(r['correct'] for r in group)} of {len(group)} | {_pct(group)} |")
    out += ["", "## Mismatches", "", "| Plan | Field | Published value | Extracted | Confidence | Cited passage |",
            "| --- | --- | --- | --- | --- | --- |"]
    for m in mismatches:
        quote = re.sub(r"\s+", " ", m["quote"]).replace("|", "/")[:90]
        out.append(f"| {m['plan']} | {m['field']} | {_show(m['expected'])} | {_show(m['extracted'])} | "
                   f"{m['confidence']:.2f} | {quote} |")
    return "\n".join(out) + "\n"
