import json, time, statistics
from groq import Groq
from src.config import GROQ_API_KEY, LLM_MODEL
from src.retriever import Retriever
from src.generator import answer, NO_ANSWER

client = Groq(api_key=GROQ_API_KEY)
qs = json.load(open("data/eval/questions.json"))
r = Retriever()

grounded, latencies = [], []
for q in qs:
    t = time.time()
    chunks = r.retrieve(q["question"])
    out = answer(q["question"], chunks)
    latencies.append(time.time() - t)
    if out["answer"] == NO_ANSWER:
        continue
    ctx = "\n\n".join(c["text"] for c in chunks)
    verdict = client.chat.completions.create(
        model=LLM_MODEL, temperature=0,
        messages=[{"role": "user", "content":
            f"Context:\n{ctx}\n\nAnswer:\n{out['answer']}\n\n"
            "Is every claim in the answer supported by the context? Reply YES or NO only."}],
    ).choices[0].message.content
    grounded.append(1 if verdict.strip().upper().startswith("YES") else 0)
    time.sleep(2)  # stay inside free rate limits

latencies.sort()
print(f"Groundedness: {sum(grounded) / max(len(grounded), 1):.2f}")
print(f"p95 latency: {latencies[int(0.95 * len(latencies)) - 1]:.2f} s")