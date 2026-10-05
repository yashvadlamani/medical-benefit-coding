"""Step 5. The sales team's workspace: accounts, the plans sold to them, and the coding review for each plan.

Reps see each account's setup status and a plain-language summary of every plan; benefit coders check each
plan against its source document and approve, edit or reject.

Reads pipeline outputs from Azure Blob Storage and stores decisions and the audit trail in Azure Table Storage.
Run locally with `flask run`; on Azure App Service it is served by gunicorn as `app:app`.

The whole site sits behind one shared password. Two settings are required:
  REVIEW_PASSWORD_HASH   a werkzeug password hash (never the password itself)
  FLASK_SECRET_KEY       random string that signs the session cookie
"""
import os
import re
from datetime import date, timedelta
from functools import lru_cache

from flask import Flask, abort, make_response, redirect, render_template, request, session, url_for
from markupsafe import Markup, escape
from werkzeug.security import check_password_hash

from benefit_coding import accounts, review, store
from benefit_coding.fields import FIELDS

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.environ.get("WEBSITE_HOSTNAME")),  # set on App Service, where HTTPS is forced
                  PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
OPEN_ENDPOINTS = {"login", "healthz", "static"}
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


@app.before_request
def require_login():
    if request.endpoint not in OPEN_ENDPOINTS and not session.get("signed_in"):
        return redirect(url_for("login", next=request.full_path.rstrip("?")))


@app.route("/login", methods=["GET", "POST"])
def login():
    password_hash = os.environ.get("REVIEW_PASSWORD_HASH", "")
    error = None if password_hash else "No password is configured for this site, so nobody can sign in."
    if request.method == "POST" and password_hash:
        if check_password_hash(password_hash, request.form.get("password", "")):
            session.clear()
            session["signed_in"] = True
            session.permanent = True
            target = request.form.get("next", "")
            # only follow a path on this site, never a full URL
            return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("index"))
        error = "That password is not correct."
    return render_template("login.html", error=error, next=request.values.get("next", "")), 401 if error else 200


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def reviewer():
    return request.cookies.get("reviewer", "").strip()


def plan_rows():
    """Every validated plan with its review progress and setup status."""
    plans = store.read_json("index.json", [])
    decided, counts = review.plan_decisions(), review.decided_counts()
    for plan in plans:
        plan["decided"] = counts.get(plan["plan_id"], 0)
        plan["status"] = accounts.plan_status(decided.get(plan["plan_id"]), plan["decided"])
    return plans


def days_until(date_text):
    return (date.fromisoformat(date_text) - date.today()).days


@app.get("/")
def index():
    """Sales view: every account, how far its plan setup has got, and how close its effective date is."""
    plans = {p["plan_id"]: p for p in plan_rows()}
    rows = []
    for account in accounts.load().values():
        sold = [plans[p] for p in account["plans"] if p in plans]
        rows.append({**account, "plan_count": len(sold), "status": accounts.rollup([p["status"] for p in sold]),
                     "ready": sum(p["status"] == accounts.READY for p in sold),
                     "open_items": sum(max(p["attention"] - p["decided"], 0) for p in sold
                                       if p["status"] != accounts.READY),
                     "days": days_until(account["effective_date"])})
    rows.sort(key=lambda a: (a["status"] == accounts.READY, a["effective_date"], a["name"]))
    return render_template("index.html", accounts=rows, reviewer=reviewer())


@app.get("/account/<account_id>")
def account(account_id):
    record = accounts.load().get(account_id)
    if record is None:
        abort(404)
    plans = {p["plan_id"]: p for p in plan_rows()}
    sold = [plans[p] for p in record["plans"] if p in plans]
    return render_template("account.html", account=record, plans=sold, days=days_until(record["effective_date"]),
                           status=accounts.rollup([p["status"] for p in sold]), reviewer=reviewer())


@app.get("/plans")
def plans():
    """Coder view: every plan regardless of account."""
    rows = plan_rows()
    owners = accounts.load()
    for row in rows:
        row["account"] = accounts.account_of(row["plan_id"], owners)
    rows.sort(key=lambda p: (not p["seeded"], p["plan_id"]))
    return render_template("plans.html", plans=rows, reviewer=reviewer())


@app.get("/plan/<plan_id>/summary")
def plan_summary(plan_id):
    """Sales view of one plan: what members pay, in plain words, without codes."""
    validated = store.read_json(f"validated/{plan_id}.json")
    if validated is None:
        abort(404)
    decisions = review.decisions(plan_id)
    meta = next((p for p in plan_rows() if p["plan_id"] == plan_id), {"plan_id": plan_id})
    sections = accounts.summary_lines(validated["fields"], decisions)
    open_lines = [line for _, lines in sections for line in lines if line["state"] not in
                  ("Confirmed", "Drafted, no issues found")]
    return render_template("summary.html", meta=meta, sections=sections, open_lines=open_lines,
                           account=accounts.account_of(plan_id), claims=validated["test_claims"], reviewer=reviewer())


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
        account=accounts.account_of(plan_id),
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
