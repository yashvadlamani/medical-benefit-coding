"""Turn a digital PDF into a scan-like copy (page images, no text layer) to exercise the OCR path.

    python ingest/make_scanned_copy.py data/raw/sbc/2026/<insurer>/<plan>_sbc.pdf
Writes data/synthetic/scanned/<name>_scanned.pdf
"""
import sys
from pathlib import Path

import pymupdf

source = Path(sys.argv[1])
out = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "scanned" / f"{source.stem}_scanned.pdf"
out.parent.mkdir(parents=True, exist_ok=True)
with pymupdf.open(source) as pdf, pymupdf.open() as scanned:
    for page in pdf:
        image = page.get_pixmap(dpi=150, colorspace=pymupdf.csGRAY)
        new_page = scanned.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=image.tobytes("jpeg", jpg_quality=60))
    scanned.save(out)
print(out)
