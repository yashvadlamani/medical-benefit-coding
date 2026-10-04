"""Step 3. Map extracted benefit fields to system codes using the code library lookup table."""
import csv
import json
from collections import Counter

from . import config
from .fields import AMOUNT, BY_NAME, COST_SHARE, FLAG


def load_library(path=None):
    """Return {(field, type, value): system_code}. Value is '' for types that carry no number."""
    with open(path or config.CODE_LIBRARY, encoding="utf-8") as f:
        return {(r["field"], r["type"], r["value"]): r["system_code"] for r in csv.DictReader(f)}


def _number(value):
    """Library values are whole numbers; 30.0 and 30 must look the same, 37.5 must not match anything."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _nearest(library, field, kind, value):
    """Closest library entries for a value the table does not hold, for the reviewer to choose from."""
    options = [(abs(float(v) - value), code) for (f, t, v), code in library.items() if f == field and t == kind]
    return [code for _, code in sorted(options)[:2]]


def _past_plan_codes(field, doc_id):
    """Codes that already-coded plans from the same insurer used for this field, most common first."""
    counts = Counter()
    if not doc_id:
        return []
    for path in (config.OUTPUT / "coded").glob(f"{doc_id[:5]}*.json"):
        if path.stem == doc_id:
            continue
        for item in json.loads(path.read_text(encoding="utf-8"))["fields"]:
            if item["field"] == field and item["status"] == "mapped":
                counts[tuple(item["codes"])] += 1
    return [list(codes) for codes, _ in counts.most_common(2)]


def map_field(item, library, doc_id=""):
    field, kind, status = item["field"], BY_NAME[item["field"]].kind, item["status"]
    result = {"field": field, "status": "mapped", "codes": [], "parameters": {}, "suggestions": [], "reason": ""}

    def lookup(type_, value=""):
        code = library.get((field, type_, value))
        if code:
            result["codes"].append(code)
        else:
            result["status"] = "unmapped"
            result["reason"] = f"no code for {type_} {value}".strip()
            if value:
                result["suggestions"] += _nearest(library, field, type_, float(value))

    if status == "not_found":
        result.update(status="no_value", reason="field was not found in the document")
    elif kind == AMOUNT:
        if status == "value":
            lookup("amount", "*")
            result["parameters"]["amount"] = item["amount"]
        else:
            lookup("not_applicable")
    elif kind == FLAG:
        lookup("flag", str(bool(item["flag"])).lower())
    elif kind == COST_SHARE:
        if status in ("no_charge", "not_covered"):
            lookup(status)
        elif status == "value":
            if item["copay"]:
                lookup("copay", _number(item["copay"]))
            if item["coinsurance_pct"]:
                lookup("coinsurance", _number(item["coinsurance_pct"]))
        else:
            result.update(status="unmapped", reason=f"no code for {status}")
        if item["deductible_applies"] is not None:
            result["parameters"]["deductible_applies"] = item["deductible_applies"]

    if result["status"] == "unmapped":
        result["codes"] = []
        result["suggestions"] += [c for codes in _past_plan_codes(field, doc_id) for c in codes
                                  if c not in result["suggestions"]]
    # a field goes to the reviewer when extraction was unsure or no code could be assigned
    result["needs_review"] = item["needs_review"] or result["status"] != "mapped"
    result["confidence"] = item["confidence"]
    result["citation"] = {"quote": item["quote"], "page": item["page"], "valid": item["citation_valid"]}
    return result


def map_plan(extraction, library=None):
    library = library or load_library()
    fields = [map_field(item, library, extraction["doc_id"]) for item in extraction["fields"]]
    return {
        "doc_id": extraction["doc_id"],
        "fields": fields,
        "summary": {
            "mapped": sum(f["status"] == "mapped" for f in fields),
            "unmapped": sum(f["status"] == "unmapped" for f in fields),
            "no_value": sum(f["status"] == "no_value" for f in fields),
            "needs_review": sum(f["needs_review"] for f in fields),
        },
    }


def save(coded):
    out = config.OUTPUT / "coded" / f"{coded['doc_id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(coded, indent=1), encoding="utf-8")
    return out
