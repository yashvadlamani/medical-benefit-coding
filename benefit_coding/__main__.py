"""Command line for the prototype pipeline.

    python -m benefit_coding run                 # ingest, extract and map all pinned plans
    python -m benefit_coding run --plan <id>     # one plan
    python -m benefit_coding run --file <pdf>    # any document, for example an unseen SBC
    python -m benefit_coding seed-codes          # load the code library CSV into Azure Table Storage
    python -m benefit_coding evaluate            # accuracy report against the published values
    python -m benefit_coding seed-mismatch       # add a demo plan with one deliberately wrong value
    python -m benefit_coding validate            # step 4: judge, reconcile and price test claims for every plan
"""
import argparse
import csv
import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, evaluate, extract, ingest, judge, mapping, store, validate


SEEDED = "-SEEDED"


def pinned_plans():
    """{plan_id: (complexity, path to SBC)} from the golden dataset."""
    with open(evaluate.GOLDEN / "selected-plans.csv", encoding="utf-8") as f:
        return {r["StandardComponentId"]: (r["complexity"], config.DATA / r["sbc_path"]) for r in csv.DictReader(f)}


def run_document(path, doc_id, skip_existing=False):
    """Steps 1 and 2 for one document. Step 3 runs afterwards so it can draw on plans already coded."""
    existing = store.read_json(f"extracted/{doc_id}.json") if skip_existing else None
    if existing:
        return existing
    document = ingest.ingest(path, doc_id)
    ingest.save(document)
    extraction = extract.extract(document)
    extract.save(extraction)
    return extraction


def seed_mismatch(plan_id):
    """Copy a plan as <id>-SEEDED with the specialist copay changed but its citation left alone,
    to show the validation step catching a value that disagrees with the SBC."""
    seeded_id = f"{plan_id}{SEEDED}"
    document = store.read_json(f"ingested/{plan_id}.json")
    extraction = copy.deepcopy(store.read_json(f"extracted/{plan_id}.json"))
    document["doc_id"] = extraction["doc_id"] = seeded_id
    item = next(f for f in extraction["fields"] if f["field"] == "specialist_visit")
    original = evaluate.actual_value(item)
    item.update(status="value", copay=float(item["copay"] or 40) + 25, coinsurance_pct=None)
    store.write_json(f"ingested/{seeded_id}.json", document)
    store.write_json(f"extracted/{seeded_id}.json", extraction)
    mapping.save(mapping.map_plan(extraction))
    return f"{seeded_id}: specialist_visit changed from {original} to a ${item['copay']:,.0f} copay"


def validate_all(workers):
    """Step 4 for every coded plan, then the index the review app lists plans from, then the report."""
    plans = pinned_plans()
    with open(evaluate.GOLDEN / "selected-plans.csv", encoding="utf-8") as f:
        details = {r["StandardComponentId"]: r for r in csv.DictReader(f)}

    def one(plan_id):
        document = store.read_json(f"ingested/{plan_id}.json")
        extraction = store.read_json(f"extracted/{plan_id}.json")
        coded = store.read_json(f"coded/{plan_id}.json")
        result = validate.validate(extraction, coded, judge.judge(document, extraction))
        store.write_json(f"validated/{plan_id}.json", result)
        return result

    plan_ids = store.names("coded")
    with ThreadPoolExecutor(workers) as pool:
        results = dict(zip(plan_ids, pool.map(one, plan_ids)))

    index = []
    for plan_id, result in results.items():
        base = details.get(plan_id.removesuffix(SEEDED), {})
        index.append({"plan_id": plan_id, "seeded": plan_id.endswith(SEEDED),
                      "issuer": base.get("IssuerMarketPlaceMarketingName", ""), "state": base.get("StateCode", ""),
                      "plan_name": base.get("PlanMarketingName", ""), "metal": base.get("MetalLevel", ""),
                      "complexity": base.get("complexity", ""), **result["summary"]})
        s = result["summary"]
        print(f"{plan_id}: {s['failed']} failed checks, {s['warnings']} warnings, {s['attention']} fields for review")
    store.write_json("index.json", index)

    text = validation_report(results, {p: c for p, (c, _) in plans.items()})
    out = config.ROOT / "docs" / "validation-report.md"
    out.write_text(text, encoding="utf-8", newline="\n")
    print(f"Report: {out}")


def validation_report(results, complexity):
    """Markdown summary of step 4, including how the LLM judge did against the published values."""
    pinned = [p for p in results if p in complexity]
    rows, _, _ = evaluate.score(pinned, complexity)
    wrong = [(r["plan"], r["field"]) for r in rows if not r["correct"]]
    right = [(r["plan"], r["field"]) for r in rows if r["correct"]]

    def verdict(plan, field):
        return (results[plan]["fields"][field]["judge"] or {}).get("verdict", "not audited")

    def flagged(plan, field):
        return results[plan]["fields"][field]["attention"]

    judge_caught = sum(verdict(*k) in ("not_supported", "unclear") for k in wrong)
    judge_false = sum(verdict(*k) in ("not_supported", "unclear") for k in right)
    confidence_caught = sum(r["needs_review"] for r in rows if not r["correct"])
    checks = [c for p in pinned for c in results[p]["checks"]]
    by_check = {}
    for c in checks:
        key = (c["check"], c["status"])
        by_check[key] = by_check.get(key, 0) + 1

    out = ["# Validation report", "",
           f"Step 4 run on {len(pinned)} plans. The LLM judge and the automated checks are compared with the values "
           "published in the CMS Exchange Public Use Files, which neither of them sees.", "",
           "## Catching wrong fields", "", "| Measure | Result |", "| --- | --- |",
           f"| Scored fields | {len(rows)} |",
           f"| Fields that disagree with the published value | {len(wrong)} |",
           f"| Wrong fields flagged by extraction confidence alone | {confidence_caught} of {len(wrong)} |",
           f"| Wrong fields flagged by the LLM judge | {judge_caught} of {len(wrong)} |",
           f"| Wrong fields sent to review after step 4 (any reason) | {sum(flagged(*k) for k in wrong)} of {len(wrong)} |",
           f"| Correct fields the judge questioned (false alarms) | {judge_false} of {len(right)} |",
           f"| Correct fields sent to review after step 4 (any reason) | {sum(flagged(*k) for k in right)} of {len(right)} |",
           f"| Plans blocked by at least one failed check | {sum(results[p]['summary']['blocked'] for p in pinned)} of {len(pinned)} |",
           "", "## Checks raised", "", "| Check | Failed | Warnings |", "| --- | --- | --- |"]
    for name in sorted({c["check"] for c in checks}):
        out.append(f"| {name} | {by_check.get((name, 'fail'), 0)} | {by_check.get((name, 'warn'), 0)} |")
    out += ["", "## Wrong fields and what the judge said", "",
            "| Plan | Field | Extracted | Judge verdict | Judge reason |", "| --- | --- | --- | --- | --- |"]
    for plan, field in wrong:
        info = results[plan]["fields"][field]
        reason = ((info["judge"] or {}).get("reason", "")).replace("|", "/")
        out.append(f"| {plan} | {field} | {info['value']} | {verdict(plan, field)} | {reason} |")
    seeded = [p for p in results if p.endswith(SEEDED)]
    out += ["", "## Seeded mismatch", ""]
    for plan in seeded:
        hits = [c for c in results[plan]["checks"] if c["field"] == "specialist_visit" and c["status"] == "fail"]
        out.append(f"`{plan}` has its specialist copay deliberately changed. Checks that caught it: "
                   + ("; ".join(f"{c['check']} ({c['detail']})" for c in hits) or "none") + ".")
    if not seeded:
        out.append("No seeded plan present. Create one with `python -m benefit_coding seed-mismatch`.")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(prog="benefit_coding", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="ingest, extract and map documents")
    run.add_argument("--plan", help="a plan id from the pinned set")
    run.add_argument("--file", help="path to any plan document")
    run.add_argument("--skip-existing", action="store_true", help="reuse saved extractions")
    run.add_argument("--workers", type=int, default=5)
    commands.add_parser("seed-codes", help="load the code library into Azure Table Storage")
    commands.add_parser("evaluate", help="write the accuracy report")
    seed = commands.add_parser("seed-mismatch", help="add a demo plan with one deliberately wrong value")
    seed.add_argument("--plan", default="38166WI0140040")
    check = commands.add_parser("validate", help="judge, reconcile and price test claims for every coded plan")
    check.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    if args.command == "seed-mismatch":
        print(seed_mismatch(args.plan))
        return
    if args.command == "validate":
        validate_all(args.workers)
        return

    if args.command == "seed-codes":
        print(f"{mapping.seed_library()} codes loaded into the {mapping.LIBRARY_TABLE} table")
        return

    plans = pinned_plans()
    if args.command == "evaluate":
        text = evaluate.report(list(plans), {p: c for p, (c, _) in plans.items()})
        out = config.ROOT / "docs" / "accuracy-report.md"
        out.write_text(text, encoding="utf-8", newline="\n")
        print(text.split("## Accuracy by field")[0])
        print(f"Full report: {out}")
        return

    if args.file:
        jobs = [(Path(args.file), Path(args.file).stem)]
    elif args.plan:
        jobs = [(plans[args.plan][1], args.plan)]
    else:
        jobs = [(path, plan_id) for plan_id, (_, path) in plans.items()]

    with ThreadPoolExecutor(args.workers) as pool:
        extractions = list(pool.map(lambda job: run_document(*job, skip_existing=args.skip_existing), jobs))

    library = mapping.load_library()
    for extraction in extractions:
        coded = mapping.map_plan(extraction, library)
        mapping.save(coded)
        s = coded["summary"]
        print(f"{coded['doc_id']}: {s['mapped']} mapped, {s['unmapped']} unmapped, "
              f"{s['no_value']} not found, {s['needs_review']} for review")


if __name__ == "__main__":
    main()
