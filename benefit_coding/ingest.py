"""Step 1. Ingest a plan document: read its text (OCR when scanned), classify it, split it into sections."""
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf

from . import config, ocr

MIN_CHARS_PER_PAGE = 80  # a page with less text than this is treated as a scan

DOCUMENT_TYPES = {
    "sbc": ["summary of benefits and coverage", "important questions", "common medical event"],
    "plan_brochure": ["outline of coverage", "certificate of coverage", "plan brochure", "benefit booklet"],
    "benefit_grid": ["schedule of benefits", "benefit grid", "benefit summary"],
    "rider": ["rider", "amendment", "endorsement"],
}

# Headings of the uniform SBC template, in the order they appear.
SBC_SECTIONS = [
    ("important_questions", r"Important\s+Questions"),
    ("common_medical_events", r"Common\s+Medical\s+Event"),
    ("excluded_and_other_services", r"Excluded\s+Services\s*&\s*Other\s+Covered\s+Services"),
    ("rights_and_notices", r"Your\s+Rights\s+to\s+Continue\s+Coverage"),
    ("coverage_examples", r"About\s+these\s+Coverage\s+Examples"),
]


@dataclass
class Section:
    name: str
    start_page: int
    end_page: int
    parts: list  # [{"page": n, "text": "..."}], so every passage keeps its page number


@dataclass
class Document:
    doc_id: str
    source: str
    doc_type: str
    page_count: int
    ocr_used: bool
    pages: list = field(default_factory=list)     # [{"page": n, "text": "..."}]
    sections: list = field(default_factory=list)  # [Section]

    def section_text(self, names=None):
        """Text of the named sections (all when None) with [[page N]] markers for citations."""
        out = []
        for section in self.sections:
            if names is None or section["name"] in names:
                out += [f"[[page {p['page']}]]\n{p['text']}" for p in section["parts"]]
        return "\n\n".join(out)


def read_pages(path):
    """Return ([page text], ocr_used). Falls back to OCR when the PDF has no usable text layer."""
    with pymupdf.open(path) as pdf:
        pages = [page.get_text() for page in pdf]
    if sum(len(p.strip()) for p in pages) >= MIN_CHARS_PER_PAGE * len(pages):
        return pages, False
    return ocr.read_pages(path), True


def classify(pages):
    """Score each document type by how many of its marker phrases appear in the first pages."""
    head = " ".join(pages[:3]).lower()
    head = re.sub(r"\s+", " ", head)
    scores = {t: sum(marker in head for marker in markers) for t, markers in DOCUMENT_TYPES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "other"


def split_sections(pages, doc_type):
    """Split an SBC at its template headings; any other document becomes one section per page."""
    if doc_type != "sbc":
        return [Section(f"page_{i}", i, i, [{"page": i, "text": t}]) for i, t in enumerate(pages, 1)]

    # locate each heading's first occurrence as (page index, offset within page)
    starts = []
    for name, pattern in SBC_SECTIONS:
        for index, text in enumerate(pages):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                starts.append((index, match.start(), name))
                break
    starts.sort()
    if not starts or starts[0][:2] != (0, 0):
        starts.insert(0, (0, 0, "header"))

    sections = []
    for (page, offset, name), nxt in zip(starts, starts[1:] + [(len(pages), 0, None)]):
        end_page, end_offset = nxt[0], nxt[1]
        parts = []
        for index in range(page, min(end_page + 1, len(pages))):
            text = pages[index]
            lo = offset if index == page else 0
            hi = end_offset if index == end_page else len(text)
            if text[lo:hi].strip():
                parts.append({"page": index + 1, "text": text[lo:hi].strip()})
        if parts:
            sections.append(Section(name, parts[0]["page"], parts[-1]["page"], parts))
    return sections


def ingest(path, doc_id=None):
    path = Path(path)
    pages, ocr_used = read_pages(path)
    doc_type = classify(pages)
    return Document(
        doc_id=doc_id or path.stem,
        source=str(path),
        doc_type=doc_type,
        page_count=len(pages),
        ocr_used=ocr_used,
        pages=[{"page": i, "text": t} for i, t in enumerate(pages, 1)],
        sections=[asdict(s) for s in split_sections(pages, doc_type)],
    )


def save(document):
    out = config.OUTPUT / "ingested" / f"{document.doc_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(document), indent=1), encoding="utf-8")
    return out


def load(doc_id):
    data = json.loads((config.OUTPUT / "ingested" / f"{doc_id}.json").read_text(encoding="utf-8"))
    return Document(**data)
