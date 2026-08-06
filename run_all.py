"""
RUN ALL — One command setup
============================
Scrapes NEA PDFs + HTML → chunks → builds vector store.
Re-run anytime NEA updates their website or PDFs.

Usage:
  python run_all.py       ← run once (or re-run on updates)
  python step5_chat.py    ← start chatting
"""

import sys

print("\n" + "=" * 55)
print("  NEA RAG Pipeline — Full Setup")
print("=" * 55)

print("\n📄 STEP 1: Scraping NEA PDFs + HTML pages...")
from step1_scraper import run_scraper
docs = run_scraper()
if not docs:
    print("\n✗ Nothing scraped. Check internet connection.")
    sys.exit(1)

print("\n✂️  STEP 2: Chunking text...")
from step2_chunker import run_chunker
run_chunker()

print("\n🧠 STEP 3: Building vector store...")
from step3_embed_and_store import run_embedder
run_embedder()

print("\n" + "=" * 55)
print("  ✅ Done! Now run: python step5_chat.py")
print("=" * 55 + "\n")
