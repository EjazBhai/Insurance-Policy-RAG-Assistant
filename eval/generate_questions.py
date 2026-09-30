"""Generate an evaluation set from your own indexed chunks.

Picks random chunks from Chroma, asks the LLM to write one question each chunk
answers, and records the chunk's source file + page as the ground truth.
Run:  python -m eval.generate_questions
Then OPEN data/eval/questions.json and delete bad/vague questions.
"""
import json
import os
import random
import time

import chromadb
from groq import Groq

from src.config import GROQ_API_KEY, LLM_MODEL, CHROMA_DIR, COLLECTION_NAME

N_QUESTIONS = 40
OUT_PATH = "data/eval/questions.json"

random.seed(42)
client = Groq(api_key=GROQ_API_KEY)

PROMPT = """Below is a passage from an insurance policy document.
Write ONE specific question a customer might ask that is fully answered by
this passage. The question must make sense on its own (never say "this
passage" or "the document") and should name the specific topic.
If the passage is only headings, boilerplate or a table of contents,
reply with exactly: SKIP
Reply with the question only.

Passage:
{passage}"""


def main():
    col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(COLLECTION_NAME)
    data = col.get(include=["documents", "metadatas"])
    pool = [(i, d, m) for i, d, m in zip(data["ids"], data["documents"], data["metadatas"])
            if len(d) >= 500]
    random.shuffle(pool)
    print(f"{len(pool)} usable chunks; generating {N_QUESTIONS} questions...")

    out = []
    for chunk_id, doc, meta in pool:
        if len(out) >= N_QUESTIONS:
            break
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL, temperature=0,
                messages=[{"role": "user", "content": PROMPT.format(passage=doc)}],
            )
        except Exception as e:
            print("  API error, skipping:", e)
            time.sleep(5)
            continue
        q = resp.choices[0].message.content.strip()
        if q.upper().startswith("SKIP") or not q.endswith("?"):
            continue
        out.append({"question": q, "source": meta["source"],
                    "page": meta["page"], "chunk_id": chunk_id})
        print(f"  {len(out):2d}. {q}")
        time.sleep(2)  # stay inside free-tier rate limits

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(out)} questions to {OUT_PATH}")
    print("NEXT: open the file and delete vague or wrong questions.")


if __name__ == "__main__":
    main()
