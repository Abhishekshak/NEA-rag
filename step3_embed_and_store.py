"""
STEP 3 — EMBED + STORE (TF-IDF, pure Python)
==============================================
No external embedding API needed. Runs fully local.

TF-IDF weakness (abbreviations like MD) is fixed by adding
synonym expansions to the text in tariff.json instead.

Run: python step3_embed_and_store.py
"""

import json
import math
import pickle
import os
import re

INPUT_FILE = "data/chunks.json"
DB_FILE    = "db/vector_store.pkl"

# Synonym map — expands abbreviations before indexing/querying
# This fixes "MD" not matching "Managing Director" etc.
SYNONYMS = {
    r'\bmd\b':                  'managing director',
    r'\bmd of nea\b':           'managing director nea',
    r'\bceo\b':                 'managing director chief executive',
    r'\bnea\b':                 'nepal electricity authority nea',
    r'\bbill\b':                'bill payment invoice',
    r'\bno.?light\b':           'no light power outage electricity',
    r'\bbijuli\b':              'bijuli electricity power',
    r'\btariff\b':              'tariff rate price unit cost',
    r'\bunit\b':                'unit kwh kilowatt',
    r'\bconnection\b':          'connection application new customer',
    r'\bcomplaint\b':           'complaint complain grievance',
    r'\bsmart meter\b':         'smart meter prepaid meter',
    r'\bload.?shedding\b':      'load shedding power cut outage',
}


def expand_synonyms(text):
    """Expand abbreviations and add synonyms to improve matching."""
    text = text.lower()
    for pattern, replacement in SYNONYMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def tokenize(text):
    text = expand_synonyms(text)
    return re.findall(r'\b[a-z]{2,}\b', text)


class VectorStore:
    def __init__(self):
        self.texts     = []
        self.vectors   = []
        self.metadatas = []
        self.vocab     = {}
        self.idf       = {}

    def _build_idf(self):
        N  = len(self.texts)
        df = {}
        for text in self.texts:
            for word in set(tokenize(text)):
                df[word] = df.get(word, 0) + 1
        self.idf   = {w: math.log(N / (c + 1)) for w, c in df.items()}
        self.vocab = {w: i for i, w in enumerate(sorted(self.idf.keys()))}

    def _vectorize(self, text):
        tokens = tokenize(text)
        tf     = {}
        for w in tokens:
            tf[w] = tf.get(w, 0) + 1
        total = len(tokens) or 1
        vec   = [0.0] * len(self.vocab)
        for w, c in tf.items():
            if w in self.vocab:
                vec[self.vocab[w]] = (c / total) * self.idf.get(w, 0)
        return vec

    def _cosine(self, a, b):
        dot = sum(x * y for x, y in zip(a, b))
        ma  = math.sqrt(sum(x * x for x in a))
        mb  = math.sqrt(sum(y * y for y in b))
        return dot / (ma * mb) if ma and mb else 0.0

    def build_index(self):
        self._build_idf()
        self.vectors = [self._vectorize(t) for t in self.texts]

    def add(self, text, metadata):
        self.texts.append(text)
        self.metadatas.append(metadata)

    def query(self, query_text, n_results=4):
        qvec   = self._vectorize(query_text)
        scores = [(self._cosine(qvec, vec), i) for i, vec in enumerate(self.vectors)]
        scores.sort(reverse=True)
        return [
            {
                "text":       self.texts[i],
                "metadata":   self.metadatas[i],
                "similarity": round(score, 4),
            }
            for score, i in scores[:n_results]
        ]

    def count(self):
        return len(self.texts)


def run_embedder():
    print("=" * 55)
    print("STEP 3: Building TF-IDF vector store")
    print("=" * 55)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\nLoaded {len(chunks)} chunks")

    store = VectorStore()
    for chunk in chunks:
        store.add(
            text=chunk["text"],
            metadata={
                "source_url":   chunk["source_url"],
                "source_title": chunk["source_title"],
                "chunk_index":  chunk["chunk_index"],
            }
        )

    print("Building index...")
    store.build_index()
    print(f"Vocabulary: {len(store.vocab)} unique terms (with synonyms)")

    os.makedirs("db", exist_ok=True)
    with open(DB_FILE, "wb") as f:
        pickle.dump(store, f)

    print(f"\n✅ Vector store saved → {DB_FILE}")
    print(f"   {store.count()} chunks stored")

    # Test abbreviation handling
    print("\n--- Retrieval tests ---")
    tests = ["MD of NEA", "managing director", "no light Baneshwor", "tariff 20 units"]
    for q in tests:
        results = store.query(q, n_results=1)
        if results:
            r = results[0]
            print(f"  '{q}' → sim={r['similarity']} | {r['metadata']['source_title']}")


if __name__ == "__main__":
    run_embedder()
