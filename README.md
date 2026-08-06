# ⚡ NEA RAG Chatbot — 100% Local with Ollama

No API key. No cost. No data leaves your PC.
Runs entirely on your machine using Ollama.

---

## 🛠️ One-time Setup

### 1. Install Ollama
Download from https://ollama.com and install it.

Then open terminal and pull the two models needed:
```bash
ollama pull llama3.2          # the chat model (~2GB)
ollama pull nomic-embed-text  # the embedding model (~270MB)
```

### 2. Install Python dependencies
```bash
pip install ollama requests beautifulsoup4
```

### 3. Start Ollama (keep this running in background)
```bash
ollama serve
```

---

## 🚀 Run the Pipeline

### Step A — Build the knowledge base (run once)
```bash
python run_all.py
```
This scrapes NEA website → chunks text → embeds with Ollama → saves to disk.
Takes 2–5 minutes depending on your PC.

### Step B — Start chatting
```bash
python step5_chat.py
```

---

## 💬 Example

```
⚡  NEA Assistant — 100% Local (Ollama + RAG)
✅ Loaded 80 NEA knowledge chunks

You: What are the tariff rates for domestic consumers?

NEA Assistant:
According to NEA's tariff schedule:
- Up to 20 units: Rs. 3.00/unit
- 21–150 units: Rs. 7.30/unit
- 151–250 units: Rs. 9.90/unit
- Above 250 units: Rs. 11.50/unit

📎 Sources: https://nea.org.np/en/pages/consumer-tariff-rates
```

---

## 📁 File Structure

```
nea-rag/
  step1_scraper.py         ← scrapes nea.org.np
  step2_chunker.py         ← splits text into 500-char chunks
  step3_embed_and_store.py ← embeds chunks with Ollama, saves to disk
  step4_rag_query.py       ← retrieval + prompt + generation logic
  step5_chat.py            ← interactive chat loop
  run_all.py               ← runs steps 1-3 in order

  data/
    scraped_documents.json ← raw scraped text
    chunks.json            ← chunked text

  db/
    vector_store.pkl       ← embeddings saved here
```

---

## 🔧 Change the Chat Model

In `step4_rag_query.py` and `step5_chat.py`, change:
```python
CHAT_MODEL = "llama3.2"
```
To any model you have pulled, e.g:
- `"mistral"` — good quality, fast
- `"phi3"` — very small, runs on low RAM
- `"gemma2"` — Google's model
- `"llama3.2:1b"` — tiny, for weak PCs

Check what you have: `ollama list`

---

## 💻 Minimum PC Requirements

| Component | Minimum |
|---|---|
| RAM | 8GB (16GB recommended) |
| Storage | 5GB free |
| OS | Windows 10 / macOS / Linux |
| Internet | Only for first-time model download + scraping |

---

## ❓ Troubleshooting

**"Ollama not running"**
→ Open a terminal and run: `ollama serve`

**"Model not found"**
→ Run: `ollama pull llama3.2`

**"HTTP 403 from NEA website"**
→ Try on home wifi instead of college network. NEA blocks some IPs.

**Slow responses**
→ Switch to a smaller model: `CHAT_MODEL = "phi3"` or `"llama3.2:1b"`
