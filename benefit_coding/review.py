"""Step 5 storage. Reviewer decisions and the audit trail, in Azure Table Storage.

  reviewdecisions   PartitionKey = plan id, RowKey = field name (or "_plan" for the plan-level decision)
  audittrail        PartitionKey = plan id, RowKey = timestamp; one row per action, never updated
"""
import uuid
from datetime import datetime, timezone

from .mapping import _table

DECISIONS_TABLE = "reviewdecisions"
AUDIT_TABLE = "audittrail"
PLAN_ROW = "_plan"
FIELD_ACTIONS = ["approve", "edit", "reject"]
PLAN_ACTIONS = ["approve", "reject", "reopen"]


def record(plan_id, target, action, reviewer, note="", ai_value="", ai_codes="", new_value="", new_codes=""):
    """Store the latest decision for a field (or the plan) and append it to the audit trail."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry = {"action": action, "reviewer": reviewer, "note": note, "ai_value": ai_value, "ai_codes": ai_codes,
             "new_value": new_value, "new_codes": new_codes, "timestamp": now}
    _table(DECISIONS_TABLE).upsert_entity({"PartitionKey": plan_id, "RowKey": target, **entry})
    _table(AUDIT_TABLE).create_entity(
        {"PartitionKey": plan_id, "RowKey": f"{now}-{uuid.uuid4().hex[:6]}", "target": target, **entry})


def decisions(plan_id):
    """{field or "_plan": latest decision} for one plan."""
    rows = _table(DECISIONS_TABLE).query_entities(f"PartitionKey eq '{plan_id}'")
    return {row["RowKey"]: dict(row) for row in rows}


def plan_decisions():
    """{plan id: plan-level decision} across all plans, for the plan list."""
    rows = _table(DECISIONS_TABLE).query_entities(f"RowKey eq '{PLAN_ROW}'")
    return {row["PartitionKey"]: dict(row) for row in rows}


def decided_counts():
    """{plan id: number of fields with a decision} across all plans."""
    counts = {}
    for row in _table(DECISIONS_TABLE).list_entities(select=["PartitionKey", "RowKey"]):
        if row["RowKey"] != PLAN_ROW:
            counts[row["PartitionKey"]] = counts.get(row["PartitionKey"], 0) + 1
    return counts


def audit(plan_id):
    """Every action taken on a plan, newest first."""
    rows = _table(AUDIT_TABLE).query_entities(f"PartitionKey eq '{plan_id}'")
    return sorted((dict(row) for row in rows), key=lambda row: row["RowKey"], reverse=True)
