"""End-to-end check: answered rate, LLM-judged groundedness, latency.
NOTE: simple LLM-as-judge, not RAGAS. Describe it that way on your resume.
Run:  python -m eval.judge
"""
import json
import time

from groq import Groq

from src.config import GROQ_API_KEY, LLM_MODEL
from src.generator import answer, NO_ANSWER
from src.retriever import Retriever

N = 30
client = Groq(api_key=GROQ_API_KEY)
qs = json.load(open("data/eval/questions.json", encoding="utf-8"))[:N]
r = Retriever()
answer("warm up", r.retrieve("warm up"))  # warm-up request, not measured

grounded, latencies, answered = [], [], 0
for q in qs:
    t = time.time()
    chunks = r.retrieve(q["question"])
    out = answer(q["question"], chunks)
    latencies.append(time.time() - t)
    if out["answer"] == NO_ANSWER:
        continue
    answered += 1
    ctx = "\n\n".join(c["text"] for c in chunks)
    verdict = client.chat.completions.create(
        model=LLM_MODEL, temperature=0,
        messages=[{"role": "user", "content":
                   f"Context:\n{ctx}\n\nAnswer:\n{out['answer']}\n\n"
                   "Is every claim in the answer supported by the context? "
                   "Reply YES or NO only."}],
    ).choices[0].message.content
    grounded.append(1 if verdict.strip().upper().startswith("YES") else 0)
    time.sleep(2)

latencies.sort()
p95 = latencies[max(int(0.95 * len(latencies)) - 1, 0)]
lines = [
    f"Questions evaluated: {len(qs)}",
    f"Answered (not 'no answer'): {answered / len(qs):.2f}",
    f"LLM-judged groundedness: {sum(grounded) / max(len(grounded), 1):.2f}",
    f"Median latency: {latencies[len(latencies) // 2]:.2f} s (retrieval + generation)",
    f"p95 latency: {p95:.2f} s",
]
text = "\n".join(lines)
print(text)
open("eval/results_generation.md", "w", encoding="utf-8").write(text + "\n")
