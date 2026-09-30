import time
from groq import Groq
from src.config import GROQ_API_KEY, LLM_MODEL

client = Groq(api_key=GROQ_API_KEY)

NO_ANSWER = "No answer found in the provided policy documents."

SYSTEM = (
    "You answer questions about insurance policies using ONLY the numbered "
    "context passages provided. Cite the passages you use like [1] or [2]. "
    "If the context does not contain the answer, reply with exactly: NO_ANSWER. "
    "Never use outside knowledge."
)


def answer(question, chunks):
    if not chunks:
        return {"answer": NO_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[{i + 1}] ({c['source']}, page {c['page']})\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    user = f"Context:\n{context}\n\nQuestion: {question}"

    for attempt in range(3):  # simple retry for rate limits
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                temperature=0,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": user}],
            )
            break
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

    text = resp.choices[0].message.content.strip()
    if "NO_ANSWER" in text:
        return {"answer": NO_ANSWER, "sources": []}

    sources = [{"file": c["source"], "page": c["page"],
                "snippet": c["text"][:200]} for c in chunks]
    return {"answer": text, "sources": sources}


if __name__ == "__main__":
    from src.retriever import Retriever
    r = Retriever()
    q = input("Question: ")
    out = answer(q, r.retrieve(q))
    print(out["answer"])
    for s in out["sources"]:
        print(f"  - {s['file']} p.{s['page']}")