"""
STEP 2 — CHUNKER
================
Splits scraped pages into small overlapping chunks.

Why overlap? So context isn't lost at chunk boundaries:
  [------chunk1------]
               [------chunk2------]

Run: python step2_chunker.py
"""

import json
import os

INPUT_FILE  = "data/scraped_documents.json"
OUTPUT_FILE = "data/chunks.json"

CHUNK_SIZE    = 500   # characters per chunk
CHUNK_OVERLAP = 100   # overlap between chunks


def split_into_chunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def run_chunker():
    print("=" * 50)
    print("STEP 2: Chunking documents")
    print("=" * 50)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    all_chunks = []
    chunk_id = 0

    for doc in documents:
        chunks = split_into_chunks(doc["text"])
        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "id":           chunk_id,
                "chunk_index":  i,
                "source_url":   doc["url"],
                "source_title": doc["title"],
                "text":         chunk_text,
            })
            chunk_id += 1
        print(f"  '{doc['title']}' → {len(chunks)} chunks")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(all_chunks)} chunks from {len(documents)} pages → {OUTPUT_FILE}")
    return all_chunks


if __name__ == "__main__":
    run_chunker()
