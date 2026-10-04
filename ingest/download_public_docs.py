"""Download the public prototype documents and optionally upload them to Azure Blob Storage.

Usage:
    python ingest/download_public_docs.py                # download into ./data
    python ingest/download_public_docs.py --upload       # also upload to the storage account

The 25 plans are pinned in ingest/plans.csv. Their SBC and brochure links come from the
CMS Exchange Plan Attributes Public Use File; the Benefits and Cost Sharing file is the answer key.
Requires curl, and the Azure CLI (logged in) for --upload.
"""
import argparse
import csv
import datetime
import hashlib
import re
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

YEAR = "2026"
PUF_BASE = f"https://download.cms.gov/marketplace-puf/{YEAR}"
PUFS = ["plan-attributes-puf", "benefits-and-cost-sharing-puf"]
REFERENCES = {
    "reference/cms-puf-data-dictionaries/planattributes-datadictionary-py26.pdf":
        "https://www.cms.gov/files/document/planattributes-datadictionary-py26.pdf",
    "reference/cms-puf-data-dictionaries/benefitscostsharing-datadictionary-py26.pdf":
        "https://www.cms.gov/files/document/benefitscostsharing-datadictionary-py26.pdf",
    "reference/av-calculator/2026-av-calculator-methodology.pdf":
        "https://www.cms.gov/files/document/updated-revised-final-2026-av-calculator-methodology-september-2025.pdf",
    "reference/sbc-template/sample-completed-sbc.pdf":
        "https://www.cms.gov/CCIIO/Resources/Forms-Reports-and-Other-Resources/Downloads/Sample-Completed-SBC-Accessible-Format-01-2020.pdf",
}
ISSUER_FOLDERS = {
    "46944": "al-bcbs-alabama",
    "32225": "mt-mountain-health-coop",
    "57601": "nh-anthem-nh-ppo",
    "96751": "nh-anthem-nh-hmo",
    "38166": "wi-security-health-plan",
}
STORAGE_ACCOUNT = "medbencodingf946de69"
CONTAINER = "prototype-docs"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
manifest = []


def fetch(url, dest, expect_pdf=True):
    """Download url to dest; returns False if a PDF was expected and something else came back."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        # some insurers publish links with a mixed-case host that curl fails on; hosts are case-insensitive
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(netloc=parts.netloc.lower()))
        subprocess.run(["curl", "-sL", "--max-time", "120", "-A", USER_AGENT, "-o", str(dest), url], check=False)
    ok = dest.exists() and (not expect_pdf or dest.read_bytes()[:5] == b"%PDF-")
    if not ok:
        dest.unlink(missing_ok=True)
    return ok


def record(path, kind, source_url, **extra):
    data = (DATA / path).read_bytes()
    manifest.append({
        "path": path, "kind": kind, "source_url": source_url, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "downloaded": datetime.date.today().isoformat(), **extra,
    })


def read_puf(name):
    """Yield the header, then each row, of the CSV inside a downloaded Public Use File zip."""
    with zipfile.ZipFile(DATA / f"raw/cms-puf/{YEAR}/{name}.zip") as z:
        with z.open(z.namelist()[0]) as f:
            text = (line.decode("utf-8-sig", errors="replace") for line in f)
            reader = csv.DictReader(text)
            yield reader.fieldnames
            yield from reader


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--upload", action="store_true", help="upload ./data to Azure Blob Storage")
    args = parser.parse_args()

    for name in PUFS:
        path = f"raw/cms-puf/{YEAR}/{name}.zip"
        url = f"{PUF_BASE}/{name}.zip"
        if not fetch(url, DATA / path, expect_pdf=False):
            raise SystemExit(f"could not download {url}")
        record(path, "cms-puf", url)

    for path, url in REFERENCES.items():
        if fetch(url, DATA / path):
            record(path, "reference", url)
        else:
            print(f"MISSING reference {url}")

    with open(ROOT / "ingest/plans.csv", encoding="utf-8") as f:
        pinned = {r["plan_id"]: r["complexity"] for r in csv.DictReader(f)}

    # one row per plan: the on-exchange standard variant
    attributes = read_puf("plan-attributes-puf")
    attr_fields = next(attributes)
    plans, attr_rows = {}, []
    for row in attributes:
        if row["StandardComponentId"] in pinned:
            attr_rows.append(row)
            if "On Exchange" in row["CSRVariationType"]:
                plans.setdefault(row["StandardComponentId"], row)
    missing = set(pinned) - set(plans)
    if missing:
        raise SystemExit(f"plans not found in the Plan Attributes file: {sorted(missing)}")

    brochures = set()
    for plan_id, row in sorted(plans.items()):
        folder = ISSUER_FOLDERS[row["IssuerId"]]
        url = row["URLForSummaryofBenefitsCoverage"]
        path = f"raw/sbc/{YEAR}/{folder}/{plan_id}_sbc.pdf"
        if fetch(url, DATA / path):
            record(path, "sbc", url, plan_id=plan_id, issuer=row["IssuerMarketPlaceMarketingName"],
                   state=row["StateCode"], plan_name=row["PlanMarketingName"], metal=row["MetalLevel"],
                   plan_type=row["PlanType"], complexity=pinned[plan_id])
        else:
            print(f"MISSING SBC {plan_id} {url}")
        url = row["PlanBrochure"]
        if url.lower().endswith(".pdf") and url not in brochures:
            brochures.add(url)
            name = re.sub(r"[^a-z0-9]+", "-", Path(urlsplit(url).path).stem.lower()).strip("-")
            path = f"raw/plan-brochures/{YEAR}/{folder}/{name}.pdf"
            if fetch(url, DATA / path):
                record(path, "plan-brochure", url, issuer=row["IssuerMarketPlaceMarketingName"], state=row["StateCode"])
            else:
                print(f"MISSING brochure {url}")

    # answer key: the published values for the pinned plans only
    golden = DATA / f"golden/{YEAR}"
    golden.mkdir(parents=True, exist_ok=True)
    with open(golden / "plan-attributes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, attr_fields)
        writer.writeheader()
        writer.writerows(attr_rows)
    record(f"golden/{YEAR}/plan-attributes.csv", "golden", "derived from plan-attributes-puf.zip", rows=len(attr_rows))

    benefits = read_puf("benefits-and-cost-sharing-puf")
    with open(golden / "benefits-and-cost-sharing.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, next(benefits))
        writer.writeheader()
        count = 0
        for row in benefits:
            if row["StandardComponentId"] in pinned:
                writer.writerow(row)
                count += 1
    record(f"golden/{YEAR}/benefits-and-cost-sharing.csv", "golden",
           "derived from benefits-and-cost-sharing-puf.zip", rows=count)

    sbc_paths = {m["plan_id"]: m for m in manifest if m["kind"] == "sbc"}
    columns = ["StandardComponentId", "StateCode", "IssuerId", "IssuerMarketPlaceMarketingName", "PlanMarketingName",
               "MetalLevel", "PlanType", "MultipleInNetworkTiers", "IsHSAEligible", "MedicalDrugDeductiblesIntegrated"]
    with open(golden / "selected-plans.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns + ["complexity", "sbc_path", "sbc_source_url"])
        for plan_id, row in sorted(plans.items()):
            sbc = sbc_paths.get(plan_id, {})
            writer.writerow([row[c] for c in columns] + [pinned[plan_id], sbc.get("path", ""), sbc.get("source_url", "")])
    record(f"golden/{YEAR}/selected-plans.csv", "golden", "derived", rows=len(plans))

    fields = ["path", "kind", "source_url", "bytes", "sha256", "downloaded", "plan_id", "issuer", "state",
              "plan_name", "metal", "plan_type", "complexity", "rows"]
    with open(DATA / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(sorted(manifest, key=lambda m: m["path"]))
    print(f"{len(manifest) + 1} files in {DATA}, {len(sbc_paths)} of {len(pinned)} SBCs")

    if args.upload:
        subprocess.run(f'az storage blob upload-batch --account-name {STORAGE_ACCOUNT} -d {CONTAINER} '
                       f'-s "{DATA}" --auth-mode key --overwrite -o none', shell=True, check=True)
        print(f"uploaded to {STORAGE_ACCOUNT}/{CONTAINER}")


if __name__ == "__main__":
    main()
