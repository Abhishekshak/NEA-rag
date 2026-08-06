"""
STEP 1 — SCRAPER (Complete Final Version)
==========================================
Covers every link visible in the NEA website navigation:
  About, Media, Consumer Services, Careers, Tenders

What loads fine with requests (plain server-side HTML):
  - About Us, Board of Directors, Org Structure, Contact
  - No-light numbers (all 9 provinces/divisions)
  - FAQ, New Connection, Meter Transfer, Bill Payment
  - Careers (recruitment pages)
  - DCS contact numbers

What's in tariff.json (PDF font unreadable by code):
  - Consumer tariff rates

What's blocked by NEA WAF entirely (returns 403/rejected):
  - Most PDFs, media/gallery pages, tender docs (dynamic)

Install: pip install requests beautifulsoup4
Run:     python step1_scraper.py
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time

OUTPUT_FILE = "data/scraped_documents.json"
TARIFF_FILE = "tariff.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ── ALL PAGES ────────────────────────────────────────────────────────────────
PAGES = [

    # ── ABOUT ─────────────────────────────────────────────────────────────
    {
        "url":   "https://nea.org.np/pages/about-us",
        "title": "About Nepal Electricity Authority (NEA)",
    },
    {
        "url":   "https://nea.org.np/boardofdirectors",
        "title": "NEA Board of Directors and Acting Managing Director",
    },
    {
        "url":   "https://nea.org.np/pages/organization-structure",
        "title": "NEA Organization Structure and Directorates",
    },
    {
        "url":   "https://nea.org.np/contact-us",
        "title": "NEA Contact Information - All Directorates",
    },

    # ── CONSUMER SERVICES → BILLING ───────────────────────────────────────
    {
        "url":   "https://nea.org.np/payment",
        "title": "NEA Bill Payment Options",
    },
    {
        "url":   "https://nea.org.np/pages/rms",
        "title": "NEA RMS Consumer Web Portal",
    },

    # ── CONSUMER SERVICES → APPLICATION FORM ─────────────────────────────
    {
        "url":   "https://nea.org.np/en/pages/new-customer-application-form",
        "title": "NEA New Customer Electricity Connection Application",
    },
    {
        "url":   "https://nea.org.np/en/pages/meter-transfer-form",
        "title": "NEA Meter Transfer Application Form",
    },

    # ── CONSUMER SERVICES → CONTACTS ─────────────────────────────────────
    {
        "url":   "https://nea.org.np/contact-information-of-dcs",
        "title": "NEA Distribution Center Service (DCS) Contact Numbers",
    },

    # No-light numbers — all 9 provinces + divisions
    {
        "url":   "https://nea.org.np/no-light-numbers/view/286",
        "title": "No Light Numbers - Koshi Province (Biratnagar)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/287",
        "title": "No Light Numbers - Madhesh Province (Janakpur)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/289",
        "title": "No Light Numbers - Bagmati Province (Kathmandu)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/292",
        "title": "No Light Numbers - Gandaki Province (Pokhara)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/290",
        "title": "No Light Numbers - Lumbini Province (Butwal)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/294",
        "title": "No Light Numbers - Karnali Province (Surkhet)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/293",
        "title": "No Light Numbers - Sudur-Paschim Province (Attaria)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/288",
        "title": "No Light Numbers - Bagmati Division (Hetauda)",
    },
    {
        "url":   "https://nea.org.np/no-light-numbers/view/291",
        "title": "No Light Numbers - Lumbini Division (Nepalgunj)",
    },

    # ── CONSUMER SERVICES → COMPLAIN ─────────────────────────────────────
    # crm.nea.org.np is a separate app, but we can store the URL info
    # in tariff.json instead — no scrapable content

    # ── CAREERS ───────────────────────────────────────────────────────────
    {
        "url":   "https://nea.org.np/recruitment/open/advertisements",
        "title": "NEA Open Recruitment Advertisements and Notices",
    },
    {
        "url":   "https://nea.org.np/recruitment/recruitment-internal/advertisements",
        "title": "NEA Internal Recruitment Advertisements",
    },
    {
        "url":   "https://nea.org.np/recruitment/open/ocurriculum",
        "title": "NEA Open Recruitment Curriculum and Syllabus",
    },
    {
        "url":   "https://nea.org.np/recruitment/open/exam-program",
        "title": "NEA Open Recruitment Exam Program",
    },
    {
        "url":   "https://nea.org.np/recruitment/open/results",
        "title": "NEA Open Recruitment Results",
    },

    # ── MEDIA / PUBLICATIONS ──────────────────────────────────────────────
    {
        "url":   "https://nea.org.np/en/category/publication-and-reports",
        "title": "NEA Publications and Reports",
    },
    {
        "url":   "https://nea.org.np/en/category/press-release",
        "title": "NEA Press Releases",
    },
    {
        "url":   "https://nea.org.np/en/category/annual-reports",
        "title": "NEA Annual Reports",
    },

    # ── FAQ ────────────────────────────────────────────────────────────────
    {
        "url":   "https://nea.org.np/en/faq",
        "title": "NEA Frequently Asked Questions (FAQ)",
    },
]


def extract_main_content(soup):
    """
    NEA pages have a large sidebar with 40+ nav links repeated on every page.
    The real content always starts AFTER the breadcrumb trail.
    Pattern: lines ["1", "Home", "2", "Page Title"] marks start of content.
    Pattern: "Highlights" or "Copyright" marks end of content.
    """
    for tag in soup(["script", "style", "footer", "iframe", "form"]):
        tag.decompose()

    lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]

    # Find breadcrumb: "1" then "Home" then "2" then page title
    start_idx = 0
    for i, line in enumerate(lines):
        if line == "Home" and i > 0 and lines[i - 1] in ["1", "1."]:
            start_idx = i + 3  # skip past "2" and "Page Title" in breadcrumb
            break

    content = lines[start_idx:]

    # Cut at footer markers
    end_idx = len(content)
    for i, line in enumerate(content):
        if line in ["Highlights", "Copyright © 2026, NEA,", "Accessibility Options"]:
            end_idx = i
            break

    return "\n".join(content[:end_idx]).strip()


def scrape_page(source):
    url   = source["url"]
    title = source["title"]

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)

        if resp.status_code == 403 or "requested URL was rejected" in resp.text:
            print(f"  ✗ Blocked by WAF — {title}")
            return None

        if resp.status_code != 200:
            print(f"  ✗ HTTP {resp.status_code} — {title}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        text = extract_main_content(soup)

        if len(text) < 80:
            # Fallback: just take everything from body if breadcrumb not found
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            text = "\n".join([l.strip() for l in text.split("\n") if l.strip()])

        if len(text) < 80:
            print(f"  ✗ No usable content — {title}")
            return None

        print(f"  ✓ {len(text):,} chars — {title}")
        return {"url": url, "title": title, "text": text}

    except Exception as e:
        print(f"  ✗ Error — {title}: {e}")
        return None


def run_scraper():
    print("=" * 60)
    print("STEP 1: Scraping NEA — Complete Coverage")
    print("=" * 60)
    print(f"Targeting {len(PAGES)} pages across all nav sections\n")

    os.makedirs("data", exist_ok=True)
    documents = []

    # Load tariff from JSON
    print("── Tariff + Static Data (tariff.json) ──────────────────")
    if not os.path.exists(TARIFF_FILE):
        print(f"  ✗ {TARIFF_FILE} not found! Add it to the folder.")
    else:
        with open(TARIFF_FILE, "r", encoding="utf-8") as f:
            tariff_docs = json.load(f)
        documents.extend(tariff_docs)
        print(f"  ✓ {len(tariff_docs)} entries loaded from tariff.json")

    # Scrape all live pages
    print("\n── Live Pages ──────────────────────────────────────────")
    success = 0
    failed  = 0

    for source in PAGES:
        doc = scrape_page(source)
        if doc:
            documents.append(doc)
            success += 1
        else:
            failed += 1
        time.sleep(0.6)  # polite delay

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Done: {len(documents)} total documents → {OUTPUT_FILE}")
    print(f"   Scraped: {success} pages  |  Failed/Blocked: {failed} pages")
    return documents


if __name__ == "__main__":
    run_scraper()
