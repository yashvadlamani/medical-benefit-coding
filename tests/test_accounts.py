from benefit_coding import accounts
from benefit_coding.fields import FIELDS


def test_seed_accounts_load_with_their_plans():
    loaded = accounts.load()
    assert loaded["A-1003"]["plans"] == ["32225MT0140001", "32225MT0140002", "32225MT0140003"]
    assert loaded["A-1003"]["employees"] == 18
    all_plans = [p for a in loaded.values() for p in a["plans"]]
    assert len(all_plans) == len(set(all_plans)) == 26  # 25 pinned plans and the seeded demo, each sold once


def test_account_of_finds_the_owner():
    assert accounts.account_of("38166WI0140040-SEEDED")["account_id"] == "A-1099"
    assert accounts.account_of("unknown") is None


def test_plan_status_follows_the_review():
    assert accounts.plan_status(None, 0) == accounts.AWAITING
    assert accounts.plan_status(None, 3) == accounts.IN_REVIEW
    assert accounts.plan_status({"action": "approve"}, 3) == accounts.READY
    assert accounts.plan_status({"action": "reject"}, 3) == accounts.RETURNED
    assert accounts.plan_status({"action": "reopen"}, 3) == accounts.IN_REVIEW


def test_account_is_only_as_ready_as_its_least_advanced_plan():
    assert accounts.rollup([accounts.READY, accounts.READY]) == accounts.READY
    assert accounts.rollup([accounts.READY, accounts.IN_REVIEW]) == accounts.IN_REVIEW
    assert accounts.rollup([accounts.IN_REVIEW, accounts.AWAITING]) == accounts.AWAITING
    assert accounts.rollup([accounts.READY, accounts.RETURNED, accounts.AWAITING]) == accounts.RETURNED
    assert accounts.rollup([]) == accounts.AWAITING


def test_summary_covers_every_field_once():
    listed = [name for _, items in accounts.SUMMARY_SECTIONS for _, name in items]
    assert sorted(listed) == sorted(f.name for f in FIELDS)


def test_summary_shows_corrections_and_what_is_still_open():
    fields = {f.name: {"value": "No charge", "attention": False} for f in FIELDS}
    fields["specialist_visit"] = {"value": "$100 copay", "attention": True}
    fields["pcp_visit"] = {"value": "$30 copay", "attention": True}
    fields["imaging"] = {"value": "20% coinsurance", "attention": True}
    decisions = {"specialist_visit": {"action": "edit", "new_value": "$75 copay"},
                 "imaging": {"action": "reject", "new_value": ""}}
    lines = {line["field"]: line for _, section in accounts.summary_lines(fields, decisions) for line in section}
    assert (lines["specialist_visit"]["value"], lines["specialist_visit"]["state"]) == ("$75 copay", "Confirmed")
    assert lines["pcp_visit"]["state"] == "Being checked"
    assert lines["imaging"]["state"] == "Being corrected"
    assert lines["preventive_care"]["state"] == "Drafted, no issues found"
