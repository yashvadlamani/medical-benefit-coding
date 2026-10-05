"""Accounts (employer groups) and the plans sold to them, as the sales team sees them.

The prototype has no real accounts, so accounts.csv holds fictional ones that group the public plans.
"""
import csv
from pathlib import Path

ACCOUNTS = Path(__file__).resolve().parent / "accounts.csv"

# Setup status of a plan, from the sales point of view. Listed from most to least in need of attention.
RETURNED = "Returned for correction"
AWAITING = "Awaiting review"
IN_REVIEW = "In review"
READY = "Ready to load"
ORDER = [RETURNED, AWAITING, IN_REVIEW, READY]

# The plan summary a rep reads: (heading, [(label, field), ...]) in the order a member would ask about them.
SUMMARY_SECTIONS = [
    ("Deductible and out-of-pocket limit", [
        ("Deductible, individual", "deductible_individual_in"),
        ("Deductible, family", "deductible_family_in"),
        ("Out-of-pocket limit, individual", "oop_max_individual_in"),
        ("Out-of-pocket limit, family", "oop_max_family_in"),
    ]),
    ("Visits and care", [
        ("Preventive care", "preventive_care"),
        ("Primary care visit", "pcp_visit"),
        ("Specialist visit", "specialist_visit"),
        ("Urgent care", "urgent_care"),
        ("Emergency room", "emergency_room"),
        ("Imaging (CT, PET, MRI)", "imaging"),
        ("Outpatient surgery", "outpatient_surgery_facility"),
        ("Hospital stay", "inpatient_facility"),
    ]),
    ("Prescription drugs", [
        ("Generic", "rx_tier1_generic"),
        ("Preferred brand", "rx_tier2_preferred_brand"),
        ("Non-preferred brand", "rx_tier3_nonpreferred_brand"),
        ("Specialty", "rx_tier4_specialty"),
    ]),
    ("Out-of-network", [
        ("Deductible, individual", "deductible_individual_oon"),
        ("Deductible, family", "deductible_family_oon"),
        ("Out-of-pocket limit, individual", "oop_max_individual_oon"),
        ("Out-of-pocket limit, family", "oop_max_family_oon"),
    ]),
    ("Prior authorization", [
        ("Prior authorization for imaging", "prior_auth_imaging"),
        ("Prior authorization for a hospital stay", "prior_auth_inpatient"),
    ]),
]


def load(path=None):
    """{account_id: account} with each account's plan ids in file order."""
    accounts = {}
    with open(path or ACCOUNTS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            account = accounts.setdefault(row["account_id"], {
                "account_id": row["account_id"], "name": row["account_name"], "state": row["state"],
                "employees": int(row["employees"]), "sales_rep": row["sales_rep"],
                "effective_date": row["effective_date"], "plans": []})
            account["plans"].append(row["plan_id"])
    return accounts


def account_of(plan_id, accounts=None):
    """The account a plan was sold to, or None."""
    return next((a for a in (accounts or load()).values() if plan_id in a["plans"]), None)


def plan_status(plan_decision, decided_fields):
    """Where a plan's setup stands. plan_decision is the plan-level review decision, if any."""
    action = (plan_decision or {}).get("action")
    if action == "approve":
        return READY
    if action == "reject":
        return RETURNED
    return IN_REVIEW if decided_fields else AWAITING


def rollup(statuses):
    """An account is only as far along as its least advanced plan."""
    return min(statuses, key=ORDER.index) if statuses else AWAITING


def summary_lines(fields, decisions):
    """The plan in plain words for a rep: [(heading, [line, ...])].

    fields is the validated record per field; decisions the reviewer's decision per field. A reviewer's
    correction replaces the drafted value. Each line says whether it is settled or still being checked.
    """
    sections = []
    for heading, items in SUMMARY_SECTIONS:
        lines = []
        for label, name in items:
            info, decision = fields[name], decisions.get(name) or {}
            action = decision.get("action")
            value = decision.get("new_value") if action == "edit" and decision.get("new_value") else info["value"]
            if action == "reject":
                state = "Being corrected"
            elif action in ("approve", "edit") or not info["attention"]:
                state = "Confirmed" if action else "Drafted, no issues found"
            else:
                state = "Being checked"
            lines.append({"label": label, "value": value, "state": state, "field": name})
        sections.append((heading, lines))
    return sections
