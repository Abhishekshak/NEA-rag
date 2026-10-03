"""
NEA RAG Chatbot — FastAPI Backend
Install: pip install fastapi uvicorn groq requests beautifulsoup4 python-dotenv
Run:     python app.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from groq import Groq
import pickle
import json
import os
import re

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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
CHAT_MODEL   = "qwen/qwen3.8-27b"
DB_FILE      = "db/vector_store.pkl"
TOP_K        = 4

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")

app    = FastAPI(title="NEA Chatbot API")
client = Groq(api_key=GROQ_API_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = None
try:
    with open(DB_FILE, "rb") as f:
        store = pickle.load(f)
    print(f"✅ Vector store loaded: {store.count()} chunks")
except FileNotFoundError:
    print("⚠️  Vector store not found. Run: python run_all.py")


class ChatRequest(BaseModel):
    message: str
    history: list = []


def clean_source_url(url):
    """Remove local file paths, only return real URLs."""
    if not url or url.startswith("local-pdf://") or url.startswith("file://"):
        return None
    return url.rstrip("/")


def retrieve(question):
    if store is None:
        return []
    search_text = question
    if re.search(r'\b(tariff|rate|electricity price)\b', question, re.I):
        search_text = re.sub(r'\b3(?:\s*[- ]?\s*phase)?\b', 'three phase', search_text, flags=re.I)
    if re.search(r'\b(no.?light|power outage)\b', question, re.I) and re.search(r'\bdurbarmarg\b', question, re.I):
        search_text += ' Kathmandu Bagmati Ratnapark'
    results = store.query(search_text, n_results=store.count())
    if re.search(r'\b(tariff|rate|electricity price)\b', question, re.I):
        results = [r for r in results if 'tariff' in r['metadata']['source_title'].lower()]
        if 'three phase' in search_text.lower():
            results.sort(key=lambda r: 'three phase' not in r['metadata']['source_title'].lower())
    elif re.search(r'\b(no.?light|power outage)\b', question, re.I):
        results = [r for r in results if 'no light' in r['metadata']['source_title'].lower()]
    return results[:TOP_K]


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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "chunks": store.count() if store else 0,
        "model": CHAT_MODEL
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if store is None:
        def err():
            yield f"data: {json.dumps({'error': 'Run python run_all.py first.'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    chunks  = retrieve(req.message)
    prompt  = build_prompt(req.message, chunks)
    sources = list(dict.fromkeys(
        clean_source_url(c["metadata"]["source_url"])
        for c in chunks
        if clean_source_url(c["metadata"]["source_url"])
    ))

    messages = list(req.history[-6:])
    messages.append({"role": "user", "content": prompt})

    def generate():
        try:
            stream = client.chat.completions.create(
                model=CHAT_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.2,
                stream=True,
            )
            for chunk in stream:
                piece = chunk.choices[0].delta.content or ""
                if piece:
                    yield f"data: {json.dumps({'text': piece})}\n\n"
            yield f"data: {json.dumps({'sources': sources, 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    print("\n⚡ NEA Chatbot → http://localhost:8000\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
