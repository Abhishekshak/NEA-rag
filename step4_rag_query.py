"""
STEP 4 — RAG QUERY ENGINE
==========================
  Retrieval : TF-IDF vector store (local, pure Python)
  Generation: Groq llama-3.3-70b-versatile (free cloud)

Run: python step4_rag_query.py
"""

import os
import pickle
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
CHAT_MODEL   = "llama-3.3-70b-versatile"
TOP_K        = 4
# ────────────────────────────────────────────────────────

groq_client = Groq(api_key=GROQ_API_KEY)


def load_store():
    with open(DB_FILE, "rb") as f:
        return pickle.load(f)


def retrieve(store, question, top_k=TOP_K):
    """TF-IDF retrieval with synonym expansion (handles MD, bijuli etc.)"""
    return store.query(question, n_results=top_k)


def build_prompt(question, chunks):
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i} — {chunk['metadata']['source_title']}]\n"
            f"URL: {chunk['metadata']['source_url']}\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)
    return f"""You are a knowledgeable and helpful assistant for Nepal Electricity Authority (NEA).
Use ONLY the context provided below to answer the question.
Give a detailed, well-structured answer. Use bullet points where appropriate.
If the answer is not in the context, say: "I don't have that specific information. Please visit nea.org.np or call 1400."
Do NOT add a Sources section — sources are handled separately.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


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
    sources = list(dict.fromkeys(c["metadata"]["source_url"] for c in chunks))
    print(f"\nAnswer:\n{answer}")
    return answer, sources


if __name__ == "__main__":
    store = load_store()
    print(f"Loaded {store.count()} chunks | Model: {CHAT_MODEL}\n")

    for q in ["Who is the MD of NEA?", "tariff for 0-20 units", "no light number Baneshwor"]:
        ask(q, store)
        print()
