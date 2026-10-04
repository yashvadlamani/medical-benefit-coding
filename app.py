"""Step 5. Review screen: a coder checks each plan against its source document and approves, edits or rejects.

Reads pipeline outputs from Azure Blob Storage and stores decisions and the audit trail in Azure Table Storage.
Run locally with `flask run`; on Azure App Service it is served by gunicorn as `app:app`.
"""
import re
from functools import lru_cache

from flask import Flask, abort, make_response, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from benefit_coding import review, store
from benefit_coding.fields import FIELDS

app = Flask(__name__)
ok = {"approve", "edit"}  # field decisions that let a plan be approved


@lru_cache(maxsize=64)
def document(plan_id):
    return store.read_json(f"ingested/{plan_id}.json")  # never changes once ingested


def highlight(text, quote):
    """Page text as HTML with the quoted passage marked. Matching ignores spacing and punctuation,
    and a quote made of separate pieces is marked piece by piece."""
    words = re.findall(r"[A-Za-z0-9]+", quote)
    spans, start = [], 0
    while start < len(words):
        for length in range(len(words) - start, 1, -1):
            pattern = r"[^A-Za-z0-9]*".join(re.escape(w) for w in words[start:start + length])
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                spans.append(match.span())
                start += length
                break
        else:
            start += 1
    out, position = [], 0
    for lo, hi in sorted(spans):
        if lo >= position:
            out += [escape(text[position:lo]), Markup("<mark>"), escape(text[lo:hi]), Markup("</mark>")]
            position = hi
    out.append(escape(text[position:]))
    return Markup("").join(out)


def reviewer():
    return request.cookies.get("reviewer", "").strip()


@app.get("/")
def index():
    plans = store.read_json("index.json", [])
    decided, counts = review.plan_decisions(), review.decided_counts()
    for plan in plans:
        decision = decided.get(plan["plan_id"])
        plan["decided"] = counts.get(plan["plan_id"], 0)
        if decision and decision["action"] in ("approve", "reject"):
            plan["review_status"] = "Approved" if decision["action"] == "approve" else "Rejected"
        else:
            plan["review_status"] = "In review" if plan["decided"] else "Not started"
    plans.sort(key=lambda p: (not p["seeded"], p["plan_id"]))
    return render_template("index.html", plans=plans, reviewer=reviewer())


@app.post("/reviewer")
def set_reviewer():
    response = make_response(redirect(request.form.get("next") or url_for("index")))
    response.set_cookie("reviewer", request.form.get("name", "").strip()[:60], max_age=60 * 60 * 24 * 90,
                        httponly=True, samesite="Lax")
    return response


@app.get("/plan/<plan_id>")
def plan(plan_id):
    validated = store.read_json(f"validated/{plan_id}.json")
    if validated is None:
        abort(404)
    extraction = {f["field"]: f for f in store.read_json(f"extracted/{plan_id}.json")["fields"]}
    coded = {f["field"]: f for f in store.read_json(f"coded/{plan_id}.json")["fields"]}
    decisions = review.decisions(plan_id)
    meta = next((p for p in store.read_json("index.json", []) if p["plan_id"] == plan_id), {"plan_id": plan_id})

    rows = []
    for field in FIELDS:
        info = validated["fields"][field.name]
        rows.append({"name": field.name, "description": field.description, "value": info["value"],
                     "attention": info["attention"], "reasons": info["reasons"], "judge": info["judge"],
                     "codes": coded[field.name]["codes"], "suggestions": coded[field.name]["suggestions"],
                     "parameters": coded[field.name]["parameters"], "confidence": extraction[field.name]["confidence"],
                     "page": extraction[field.name]["page"], "quote": extraction[field.name]["quote"],
                     "decision": decisions.get(field.name)})
    rows.sort(key=lambda r: not r["attention"])  # stable: flagged fields first, otherwise plan order

    # the source pane shows the page cited by the selected field, with the quote marked
    pages = document(plan_id)["pages"]
    selected = next((r for r in rows if r["name"] == request.args.get("field")), None)
    page_number = request.args.get("page", type=int) or (selected and selected["page"]) or 1
    page_number = min(max(page_number, 1), len(pages))
    page_text = pages[page_number - 1]["text"]
    source = highlight(page_text, selected["quote"]) if selected and selected["page"] == page_number else escape(page_text)

    pending = [r["name"] for r in rows if r["attention"] and (not r["decision"] or r["decision"]["action"] not in ok)]
    return render_template(
        "plan.html", meta=meta, rows=rows, validated=validated, selected=selected, source=source,
        page_number=page_number, page_count=len(pages), pending=pending, plan_decision=decisions.get(review.PLAN_ROW),
        audit=review.audit(plan_id), reviewer=reviewer())


@app.post("/plan/<plan_id>/field/<field>")
def decide_field(plan_id, field):
    action = request.form.get("action")
    validated = store.read_json(f"validated/{plan_id}.json")
    if validated is None or field not in validated["fields"] or action not in review.FIELD_ACTIONS:
        abort(400)
    if not reviewer():
        return redirect(url_for("plan", plan_id=plan_id, field=field, error="name"))
    new_value, new_codes = request.form.get("new_value", "").strip(), request.form.get("new_codes", "").strip()
    if action == "edit" and not (new_value or new_codes):
        return redirect(url_for("plan", plan_id=plan_id, field=field, error="edit"))
    coded = next(f for f in store.read_json(f"coded/{plan_id}.json")["fields"] if f["field"] == field)
    review.record(plan_id, field, action, reviewer(), note=request.form.get("note", "").strip()[:500],
                  ai_value=validated["fields"][field]["value"], ai_codes=", ".join(coded["codes"]),
                  new_value=new_value[:200] if action == "edit" else "",
                  new_codes=new_codes[:200] if action == "edit" else "")
    return redirect(url_for("plan", plan_id=plan_id, field=field) + f"#{field}")


@app.post("/plan/<plan_id>/decision")
def decide_plan(plan_id):
    action = request.form.get("action")
    validated = store.read_json(f"validated/{plan_id}.json")
    if validated is None or action not in review.PLAN_ACTIONS:
        abort(400)
    if not reviewer():
        return redirect(url_for("plan", plan_id=plan_id, error="name"))
    if action == "approve":
        decisions = review.decisions(plan_id)
        pending = [name for name, info in validated["fields"].items()
                   if info["attention"] and decisions.get(name, {}).get("action") not in ok]
        if pending:  # the load gate: nothing is approved while a flagged field is undecided or rejected
            return redirect(url_for("plan", plan_id=plan_id, error="pending"))
    review.record(plan_id, review.PLAN_ROW, action, reviewer(), note=request.form.get("note", "").strip()[:500])
    return redirect(url_for("plan", plan_id=plan_id))


@app.get("/healthz")
def healthz():
    return "ok"
