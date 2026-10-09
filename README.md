# Policy RAG Assistant

Ask questions about insurance policy documents and get **source-cited answers**.
Retrieval is hybrid (semantic + BM25) with a cross-encoder re-ranker, and the
LLM is instructed to answer only from the retrieved passages or say
"No answer found."

Built with free tools only: local embeddings, local vector DB, and Groq's free API.

## Architecture

```mermaid
flowchart LR
    A[Policy PDFs] --> B[ingest.py: extract, chunk, embed]
    B --> C[(Chroma vector DB)]
    Q[User question] --> D[Semantic search]
    Q --> E[BM25 keyword search]
    C --> D
    C --> E
    D --> F[Reciprocal Rank Fusion]
    E --> F
    F --> G[Cross-encoder re-rank]
    G --> H[Groq Llama 3.3 70B: grounded answer + citations]
    H --> I[FastAPI /ask]
```

## Stack

| Part | Choice |
|---|---|
| Embeddings | `BAAI/bge-small-en-v1.5` (local) |
| Vector DB | Chroma (local, persistent) |
| Keyword search | `rank-bm25` |
| Re-ranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | Llama 3.3 70B via Groq free tier |
| API | FastAPI |

## Setup

```bash
git clone https://github.com/EjazBhai/Insurance-Policy-RAG-Assistant.git
cd Insurance-Policy-RAG-Assistant
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

1. Create `.env` with `GROQ_API_KEY=your_key` (free key at console.groq.com).
2. Put policy PDFs in `data/raw/` (see sources below).
3. Build the index and start the API:

```bash
python -m src.ingest
uvicorn src.api:app --reload
```

Open http://127.0.0.1:8000/docs and try `POST /ask`.

## Example

Request:
```json
{ "question": "Is dental treatment covered?" }
```
Response (shortened):
```json
{
  "answer": "Dental treatment is not covered under the policy unless it requires hospitalisation. [1]",
  "sources": [{ "file": "Health Protector Policy Wording.pdf", "page": 12, "snippet": "..." }],
  "latency_ms": 2300
}
```
Questions outside the documents return `"No answer found in the provided policy documents."`

## Evaluation

The project includes a 40-question retrieval benchmark and a separate generation evaluation to assess retrieval quality, answer grounding, and latency.

### Retrieval Evaluation

A retrieval hit means the expected source file and page appear within the top 5 retrieved results.

| Retrieval strategy | Hit Rate@5 | MRR |
|---|---:|---:|
| Semantic search | 78% | 0.630 |
| Hybrid search (semantic + BM25) | 82% | 0.670 |
| Hybrid search + re-ranking | **93%** | **0.790** |

**Key finding:** Hybrid retrieval with re-ranking achieved the highest measured retrieval performance on the 40-question evaluation set.

### Generation Evaluation

| Metric | Measured result |
|---|---:|
| Questions evaluated | 30 |
| Answered rate | 100% |
| LLM-judged groundedness | 97% |
| Median latency | 9.05 seconds |
| P95 latency | 11.82 seconds |

Groundedness is estimated using an LLM judge and should not be interpreted as a human-verified accuracy score.

### How to Reproduce

Run the evaluation modules from the project environment:

```bash
python -m eval.hit_rate
python -m eval.judge
```

The generation evaluation requires the configured LLM API credentials. Results are saved in the evaluation reports.

### Evaluation Limitations

- The benchmark contains 40 labelled retrieval questions and 30 generation-evaluation questions.
- Evaluation questions were generated from indexed chunks, so wording overlap may make retrieval results optimistic.
- Groundedness is scored by an LLM judge, not independently verified by human reviewers.
- Similar wording across insurance documents can affect source matching.
- Scanned image-only PDFs are not supported without OCR.
- Latency and API availability depend on the model provider and runtime environment.


## Source documents

Public policy wordings, downloaded from insurers' websites (not redistributed in this repo):

- Universal Sompo, A Plus Health: https://www.universalsompo.com/assets/file/a-plus-health-insurance/a-plus-health-insurance-policy-wording.pdf
- IFFCO Tokio, Health Protector: https://www.iffcotokio.co.in/content/dam/iffcotokio/iffco-pdf/sites/default/files/pdf/Health%20Protector%20Policy%20Wording.pdf
- United India, Individual Health Insurance prospectus: https://uiic.co.in/web/sites/default/files/Policy-Document/20240325_Prospectus_IHIP.pdf
- Religare, Health Care Advantage: https://www.eindiainsurance.com/brochure/religare-health-care-advantage-policy-wordings.pdf

## Docker (optional)

```bash
docker build -t policy-rag .
docker run -p 8000:8000 --env-file .env -v ${PWD}/chroma_db:/app/chroma_db policy-rag
```

## License

MIT, see [LICENSE](LICENSE).
