"""
STEP 5 — INTERACTIVE CHAT
==========================
Terminal chat. Streams answers word by word from Groq.

Your laptop : scraping, chunking, TF-IDF retrieval (pure Python)
Groq cloud  : LLM generation (Llama 3.3 70B, free)
Ollama      : NOT needed at all

Run: python step5_chat.py
"""

import pickle
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
# from step4_rag_query import retrieve, build_prompt, groq_client, GROQ_MODEL  //old
from step4_rag_query import retrieve, build_prompt, groq_client, CHAT_MODEL

DB_FILE = "db/vector_store.pkl"


def chat():
    print("\n" + "=" * 55)
    print("  ⚡  NEA Assistant — Local RAG + Groq Cloud")
    print("=" * 55)
    print(f"  Embeddings : TF-IDF (pure Python, no installs)")
    print(f"  Generation : {CHAT_MODEL} (Groq, free)")
    print(f"  Ollama     : not needed")
    print(f"  Cost       : Rs. 0")
    print("  Type 'quit' to exit.\n")

    try:
        with open(DB_FILE, "rb") as f:
            store = pickle.load(f)
        print(f"  ✅ Loaded {store.count()} NEA knowledge chunks\n")
    except FileNotFoundError:
        print("  ✗ Vector store not found!")
        print("    Run: python run_all.py  first.\n")
        return

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye! Bijuli baal ⚡")
            break

        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Bye! Bijuli baal ⚡")
            break

        # Retrieve relevant chunks (pure Python, local)
        chunks  = retrieve(store, user_input)
        prompt  = build_prompt(user_input, chunks)
        history.append({"role": "user", "content": prompt})

        # Stream answer from Groq
        try:
            print("\nNEA Assistant: ", end="", flush=True)
            answer = ""

            stream = groq_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=history,
                max_tokens=1024,
                temperature=0.2,
                stream=True,
            )

            for chunk in stream:
                piece = chunk.choices[0].delta.content or ""
                print(piece, end="", flush=True)
                answer += piece

            print()

            history.append({"role": "assistant", "content": answer})

            sources = list({c["metadata"]["source_url"] for c in chunks})
            print(f"\n  📎 Sources: {', '.join(sources)}\n")

        except Exception as e:
            print(f"\n  ✗ Groq error: {e}")
            print("  Check your GROQ_API_KEY in step4_rag_query.py\n")


if __name__ == "__main__":
    chat()
