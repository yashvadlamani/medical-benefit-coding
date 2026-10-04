"""LLM-as-judge: a second model call that audits each extracted value against the document."""
import json

from openai import AzureOpenAI

from . import config, extract
from .fields import FIELDS, describe

VERDICTS = ["supported", "not_supported", "unclear"]

SYSTEM_PROMPT = """You audit values that an extraction system pulled from a health plan document.
For every claim, read the document yourself and decide whether it supports the claimed value for that field.

- "supported": the document states this value for this field, following the extraction rules below.
- "not_supported": the document states a different value, the value comes from the wrong row, column, tier or
  network, or the quoted passage does not exist or does not say this.
- "unclear": the document is ambiguous, or a reasonable coder could read it either way.

Judge only against the document. Do not assume the extraction is right. Give a reason of one short sentence
that names the value you see in the document when it differs.

The extraction was asked to follow these rules:
"""


def _schema():
    item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "field": {"type": "string", "enum": [f.name for f in FIELDS]},
            "verdict": {"type": "string", "enum": VERDICTS},
            "reason": {"type": "string"},
        },
        "required": ["field", "verdict", "reason"],
    }
    return {
        "name": "verdicts",
        "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
                   "properties": {"verdicts": {"type": "array", "items": item}}, "required": ["verdicts"]},
    }


def judge(document, extraction):
    """Return {field: {"verdict", "reason"}} for every field that has a value to audit."""
    claims = [f"- {item['field']} ({item['kind']}): {describe(item)}. Quoted passage (page {item['page']}): "
              f"\"{' '.join(item['quote'].split())}\""
              for item in extraction["fields"] if item["status"] != "not_found"]
    if not claims:
        return {}
    names = extract.SBC_SECTIONS_USED if document["doc_type"] == "sbc" else None
    text = "\n\n".join(f"[[page {part['page']}]]\n{part['text']}" for section in document["sections"]
                       if names is None or section["name"] in names for part in section["parts"])
    client = AzureOpenAI(azure_endpoint=config.setting("AZURE_AI_ENDPOINT"), api_key=config.setting("AZURE_AI_KEY"),
                         api_version="2024-10-21", max_retries=6)
    response = client.chat.completions.create(
        model=config.setting("AZURE_OPENAI_JUDGE_DEPLOYMENT", config.setting("AZURE_OPENAI_DEPLOYMENT")),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + extract.SYSTEM_PROMPT},
            {"role": "user", "content": "Claims to audit:\n" + "\n".join(claims) + f"\n\nDocument:\n\n{text}"},
        ],
        response_format={"type": "json_schema", "json_schema": _schema()},
    )
    audited = {item["field"] for item in extraction["fields"] if item["status"] != "not_found"}
    return {v["field"]: {"verdict": v["verdict"], "reason": v["reason"]}
            for v in json.loads(response.choices[0].message.content)["verdicts"] if v["field"] in audited}
