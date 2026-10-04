"""Command line for the prototype pipeline.

    python -m benefit_coding run                 # ingest, extract and map all pinned plans
    python -m benefit_coding run --plan <id>     # one plan
    python -m benefit_coding run --file <pdf>    # any document, for example an unseen SBC
    python -m benefit_coding seed-codes          # load the code library CSV into Azure Table Storage
    python -m benefit_coding evaluate            # accuracy report against the published values
"""
import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config, evaluate, extract, ingest, mapping


def pinned_plans():
    """{plan_id: (complexity, path to SBC)} from the golden dataset."""
    with open(evaluate.GOLDEN / "selected-plans.csv", encoding="utf-8") as f:
        return {r["StandardComponentId"]: (r["complexity"], config.DATA / r["sbc_path"]) for r in csv.DictReader(f)}


def run_document(path, doc_id, skip_existing=False):
    """Steps 1 and 2 for one document. Step 3 runs afterwards so it can draw on plans already coded."""
    extracted_path = config.OUTPUT / "extracted" / f"{doc_id}.json"
    if skip_existing and extracted_path.exists():
        return json.loads(extracted_path.read_text(encoding="utf-8"))
    document = ingest.ingest(path, doc_id)
    ingest.save(document)
    extraction = extract.extract(document)
    extract.save(extraction)
    return extraction


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
    args = parser.parse_args()

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
