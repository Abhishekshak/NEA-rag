"""
NEA RAG Chatbot — FastAPI Backend
Install: pip install fastapi uvicorn groq requests beautifulsoup4
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
CHAT_MODEL   = "llama-3.3-70b-versatile"
DB_FILE      = "db/vector_store.pkl"
TOP_K        = 4

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


def retrieve(question):
    if store is None:
        return []
    return store.query(question, n_results=TOP_K)


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


@app.get("/health")
def health():
    return {"status": "ok", "chunks": store.count() if store else 0, "model": CHAT_MODEL}


@app.post("/chat")
async def chat(req: ChatRequest):
    if store is None:
        def err():
            yield f"data: {json.dumps({'error': 'Run python run_all.py first.'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    chunks  = retrieve(req.message)
    prompt  = build_prompt(req.message, chunks)
    sources = list(dict.fromkeys(c["metadata"]["source_url"] for c in chunks))

    messages = [t for t in req.history[-6:]]
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
