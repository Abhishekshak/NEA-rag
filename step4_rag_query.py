"""
STEP 4 — RAG QUERY ENGINE
==========================
  Retrieval : TF-IDF vector store (local, pure Python)
  Generation: Groq qwen/qwen3.8-27b (free tier)

Run: python step4_rag_query.py
"""

import os
import pickle
import re
from groq import Groq

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

# ── CONFIG ──────────────────────────────────────────────
DB_FILE      = "db/vector_store.pkl"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CHAT_MODEL   = "qwen/qwen3.8-27b"
TOP_K        = 4
# ────────────────────────────────────────────────────────

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")

groq_client = Groq(api_key=GROQ_API_KEY)


def load_store():
    with open(DB_FILE, "rb") as f:
        return pickle.load(f)


def clean_source_url(url):
    """Remove local file paths, only return real URLs."""
    if not url or url.startswith("local-pdf://") or url.startswith("file://"):
        return None
    return url.rstrip("/")


def retrieve(store, question, top_k=TOP_K):
    """TF-IDF retrieval with synonym expansion."""
    search_text = question
    if re.search(r'\b(tariff|rate|electricity price)\b', question, re.I):
        search_text = re.sub(r'\b3(?:\s*[- ]?\s*phase)?\b', 'three phase', search_text, flags=re.I)
    if re.search(r'\b(no.?light|power outage)\b', question, re.I) and re.search(r'\bdurbarmarg\b', question, re.I):
        # NEA's indexed outage list is organized by service area; Durbarmarg
        # itself is not listed, while the Kathmandu service-area list is relevant.
        search_text += ' Kathmandu Bagmati Ratnapark'
    results = store.query(search_text, n_results=store.count())
    if re.search(r'\b(tariff|rate|electricity price)\b', question, re.I):
        results = [r for r in results if 'tariff' in r['metadata']['source_title'].lower()]
        if 'three phase' in search_text.lower():
            results.sort(key=lambda r: 'three phase' not in r['metadata']['source_title'].lower())
    elif re.search(r'\b(no.?light|power outage)\b', question, re.I):
        results = [r for r in results if 'no light' in r['metadata']['source_title'].lower()]
    return results[:top_k]


def build_prompt(question, chunks):
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i} — {chunk['metadata']['source_title']}]\n"
            f"URL: {chunk['metadata']['source_url']}\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return f"""You are a friendly and knowledgeable assistant for Nepal Electricity Authority (NEA).

INSTRUCTIONS:
- If the user sends a greeting (like "hi", "hello", "namaste", "how are you", etc.) or any casual/non-NEA message, respond warmly and naturally. Tell them you are the NEA assistant and list what you can help with (tariffs, no-light numbers, new connections, bill payment, careers, projects, etc.).
- For NEA-related questions, use ONLY the context below to answer.
- Give detailed, well-structured answers with bullet points where appropriate.
- If a specific NEA question is not answered in the context, say: "I don't have that specific information. Please visit nea.org.np or call 1400."
- For location questions, do not present a nearby service area's number as the exact requested location. If context has a likely nearby listing, name that locality and clearly say the exact location was not listed.
- Do NOT add a Sources section.

CONTEXT:
{context}

USER: {question}

RESPONSE:"""


def ask(question, store):
    print(f"\nQuestion: {question}")
    print("-" * 50)

    chunks = retrieve(store, question)
    for c in chunks:
        print(f"  sim={c['similarity']} | {c['metadata']['source_title']}")

    prompt   = build_prompt(question, chunks)
    response = groq_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.2,
    )

    answer  = response.choices[0].message.content
    sources = list(dict.fromkeys(
        clean_source_url(c["metadata"]["source_url"])
        for c in chunks
        if clean_source_url(c["metadata"]["source_url"])
    ))

    print(f"\nAnswer:\n{answer}")
    return answer, sources


if __name__ == "__main__":
    store = load_store()
    print(f"Loaded {store.count()} chunks | Model: {CHAT_MODEL}\n")

    for q in ["hi", "hello", "how are you", "Who is the MD of NEA?",
              "tariff for 0-20 units", "no light number Baneshwor"]:
        ask(q, store)
        print()
