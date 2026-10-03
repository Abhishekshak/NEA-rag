"""
STEP 1B — PDF INGESTION
=========================
Extracts real text from every PDF placed in pdfs/ and turns each one
into RAG-ready document(s), same shape as the scraped web pages.

Previously, the Consumer Tariff PDF was never opened by any code —
its numbers were manually retyped into tariff.json. This step reads
the actual PDF bytes with pdfplumber, so:
  - the PDF genuinely flows through ingestion -> chunking -> embedding
  - any PDF you drop into pdfs/ later is picked up automatically,
    no manual retyping needed
  - nothing here touches tariff.json's curated English summaries —
    those still ship separately, since they're easier for the LLM to
    quote directly. This step only ADDS documents, never removes any.

Install: pip install pdfplumber
Run:     python step1b_pdf_ingest.py   (also called by step1_scraper.py)
"""

import os

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

PDF_DIR = "pdfs"

# Friendlier titles for PDFs we know about. Any PDF without an entry
# here still gets ingested — it just gets a title derived from its
# filename instead.
KNOWN_TITLES = {
    "Consumer_Tarrif_data.pdf": "NEA Consumer Electricity Tariff Rates (Official PDF, full detail)",
}

# Very long PDFs are split into part-documents so the chunker/embedder
# handle them the same way it handles any other document.
MAX_CHARS_PER_DOC = 6000


def _title_for(filename):
    if filename in KNOWN_TITLES:
        return KNOWN_TITLES[filename]
    name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    return f"NEA Document — {name}"


def extract_pdf_text(path):
    """Returns list of per-page extracted text (non-empty pages only)."""
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(text)
    return pages


def run_pdf_ingest():
    print("── PDF Documents (pdfs/) ────────────────────────────────")
    documents = []

    if pdfplumber is None:
        print("  ✗ pdfplumber not installed. Run: pip install pdfplumber")
        return documents

    if not os.path.isdir(PDF_DIR):
        print(f"  ✗ {PDF_DIR}/ folder not found — skipping")
        return documents

    pdf_files = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    if not pdf_files:
        print(f"  ✗ No PDFs found in {PDF_DIR}/")
        return documents

    for filename in pdf_files:
        path = os.path.join(PDF_DIR, filename)
        title = _title_for(filename)
        try:
            pages = extract_pdf_text(path)
            full_text = "\n\n".join(pages)

            if len(full_text) < 40:
                print(f"  ✗ {filename}: no extractable text found (scanned image? would need OCR)")
                continue

            if len(full_text) <= MAX_CHARS_PER_DOC:
                documents.append({
                    "url":   f"local-pdf://{filename}",
                    "title": title,
                    "text":  full_text,
                })
            else:
                start, part = 0, 1
                while start < len(full_text):
                    piece = full_text[start:start + MAX_CHARS_PER_DOC]
                    documents.append({
                        "url":   f"local-pdf://{filename}#part{part}",
                        "title": f"{title} (Part {part})",
                        "text":  piece,
                    })
                    start += MAX_CHARS_PER_DOC
                    part += 1

            print(f"  ✓ {filename}: {len(full_text):,} chars extracted across {len(pages)} pages "
                  f"-> {max(1, -(-len(full_text) // MAX_CHARS_PER_DOC))} document(s)")

        except Exception as e:
            print(f"  ✗ {filename}: failed to extract — {e}")

    print(f"  → {len(documents)} document(s) added from PDFs")
    return documents


if __name__ == "__main__":
    run_pdf_ingest()
