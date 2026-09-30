import json
from src.retriever import Retriever

qs = json.load(open("data/eval/questions.json"))
r = Retriever()

for mode in ["semantic", "hybrid", "hybrid_rerank"]:
    hits = 0
    for q in qs:
        results = r.retrieve(q["question"], mode=mode, k=5)
        if any(c["source"] == q["source"] and c["page"] == q["page"] for c in results):
            hits += 1
    print(f"{mode:15s} hit rate@5 = {hits / len(qs):.2f}")