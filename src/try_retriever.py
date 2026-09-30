from src.retriever import Retriever

r = Retriever()
q = "Is dental treatment covered?"
for mode in ["semantic", "hybrid", "hybrid_rerank"]:
    print(f"\n--- {mode} ---")
    for c in r.retrieve(q, mode=mode, k=3):
        print(f"{c['source']} p.{c['page']}: {c['text'][:120]!r}")
        