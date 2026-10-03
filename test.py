import json
docs = json.load(open("data/scraped_documents.json", encoding="utf-8"))
for d in docs:
    if "Bagmati Province" in d["title"]:
        print(repr(d["text"]))