"""Retrieval quality: hit rate@5 and MRR for each retrieval mode.
Run:  python -m eval.hit_rate
"""
import json

from src.retriever import Retriever

K = 5
qs = json.load(open("data/eval/questions.json", encoding="utf-8"))
r = Retriever()
r.retrieve("warm up", mode="hybrid_rerank")  # load models before measuring

rows = []
for mode in ["semantic", "hybrid", "hybrid_rerank"]:
    hits, rr = 0, 0.0
    for q in qs:
        results = r.retrieve(q["question"], mode=mode, k=K)
        for rank, c in enumerate(results, start=1):
            if c["source"] == q["source"] and c["page"] == q["page"]:
                hits += 1
                rr += 1 / rank
                break
    rows.append((mode, hits / len(qs), rr / len(qs)))

lines = [f"Questions: {len(qs)}", "",
         "| Mode | Hit rate@5 | MRR |", "|---|---|---|"]
lines += [f"| {m} | {h:.2f} | {mrr:.2f} |" for m, h, mrr in rows]
text = "\n".join(lines)
print(text)
open("eval/results_retrieval.md", "w", encoding="utf-8").write(text + "\n")
