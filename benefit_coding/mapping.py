"""Step 3. Map extracted benefit fields to system codes.

The code library and the codes assigned to each plan are held in Azure Table Storage:
  codelibrary   PartitionKey = field, RowKey = "<type>:<value>", system_code, description
  codedplans    PartitionKey = insurer id (first 5 characters of the plan id), RowKey = "<plan id>:<field>"
"""
import csv
import json
from collections import Counter

from azure.data.tables import TableServiceClient

from . import config, store
from .fields import AMOUNT, BY_NAME, COST_SHARE, FLAG


LIBRARY_TABLE = "codelibrary"
PLANS_TABLE = "codedplans"


def _table(name):
    service = TableServiceClient.from_connection_string(config.setting("AZURE_STORAGE_CONNECTION_STRING"))
    return service.create_table_if_not_exists(name)


def read_seed(path=None):
    """Return {(field, type, value): system_code} from the seed CSV. Value is '' for types with no number."""
    with open(path or config.CODE_LIBRARY, encoding="utf-8") as f:
        return {(r["field"], r["type"], r["value"]): r["system_code"] for r in csv.DictReader(f)}


def seed_library(path=None):
    """Load the seed CSV into the codelibrary table, replacing rows with the same key."""
    table = _table(LIBRARY_TABLE)
    with open(path or config.CODE_LIBRARY, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for field in sorted({r["field"] for r in rows}):
        batch = [("upsert", {"PartitionKey": field, "RowKey": f"{r['type']}:{r['value']}", "type": r["type"],
                             "value": r["value"], "system_code": r["system_code"], "description": r["description"]})
                 for r in rows if r["field"] == field]
        for start in range(0, len(batch), 100):  # a table transaction holds at most 100 rows of one partition
            table.submit_transaction(batch[start:start + 100])
    return len(rows)


def load_library():
    """Return {(field, type, value): system_code} from the codelibrary table."""
    entities = _table(LIBRARY_TABLE).list_entities()
    library = {(e["PartitionKey"], e["type"], e["value"]): e["system_code"] for e in entities}
    if not library:
        raise RuntimeError("the codelibrary table is empty; run: python -m benefit_coding seed-codes")
    return library


def _number(value):
    """Library values are whole numbers; 30.0 and 30 must look the same, 37.5 must not match anything."""
    return str(int(value)) if float(value).is_integer() else str(value)


def _nearest(library, field, kind, value):
    """Closest library entries for a value the table does not hold, for the reviewer to choose from."""
    options = [(abs(float(v) - value), code) for (f, t, v), code in library.items() if f == field and t == kind]
    return [code for _, code in sorted(options)[:2]]


def _past_plan_codes(field, doc_id):
    """Codes that already-coded plans from the same insurer used for this field, most common first."""
    if not doc_id:
        return []
    counts = Counter()
    query = f"PartitionKey eq '{doc_id[:5]}' and field eq '{field}' and status eq 'mapped'"
    for entity in _table(PLANS_TABLE).query_entities(query):
        if entity["plan_id"] != doc_id:
            counts[tuple(json.loads(entity["codes"]))] += 1
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
    """Write the coded plan to the codedplans table, and to blob storage for the review app."""
    plan_id = coded["doc_id"]
    batch = [("upsert", {
        "PartitionKey": plan_id[:5], "RowKey": f"{plan_id}:{f['field']}", "plan_id": plan_id, "field": f["field"],
        "status": f["status"], "codes": json.dumps(f["codes"]), "parameters": json.dumps(f["parameters"]),
        "suggestions": json.dumps(f["suggestions"]), "needs_review": f["needs_review"], "confidence": f["confidence"],
        "citation_quote": f["citation"]["quote"], "citation_page": f["citation"]["page"] or 0,
    }) for f in coded["fields"]]
    _table(PLANS_TABLE).submit_transaction(batch)

    store.write_json(f"coded/{plan_id}.json", coded)
