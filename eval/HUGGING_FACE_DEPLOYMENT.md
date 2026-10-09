# Hugging Face deployment for the Evaluation Lab

This deploys a **separate, read-only Evaluation Lab Space**. It does not overwrite the existing `Insurance-Policy-RAG-Assistant` Space or the FastAPI backend Dockerfile in the main repository.

## 1. Run evaluations locally first

From the main repository root in PowerShell, ensure your private `.env` contains a valid `GROQ_API_KEY` and that local `data/raw/` PDFs + `chroma_db/` are present. If the local index is not present, run:

```powershell
python scripts/download_pdfs.py
python -m src.ingest
```

Then run retrieval evaluation (no LLM generation calls are needed for this step):

```powershell
python -m eval.hit_rate --k 5
```

Run generation evaluation (uses your private Groq key and may take several minutes):

```powershell
python -m eval.judge --limit 30 --delay 4
```

Expected outputs:

- `eval/results_retrieval.json` and `eval/results_retrieval.md`
- `eval/results_generation.json` and `eval/results_generation.md`

These reports contain metrics, per-question diagnostics, and judgements—not API keys or generated answer text. Review the output before publishing it. Do not add `.env`, `data/raw/*.pdf`, or `chroma_db/` to the Space.

## 2. Preview the dashboard locally

Install dashboard dependencies in your existing environment, then launch:

```powershell
pip install -r eval/hf_space/requirements.txt
streamlit run eval/dashboard.py
```

It reads the local report JSON automatically. You can also use the sidebar upload controls to preview report JSON files without saving them.

## 3. Create a new Space

1. Open https://huggingface.co/new-space while signed in.
2. Use a new name such as `insurance-policy-rag-evaluation`.
3. Select **Docker** as the SDK and **CPU Basic** hardware to start.
4. Choose public visibility only after reviewing report outputs. Do not add an API secret to this visualization-only Space.
5. Create the Space and follow its Git clone instructions.

Use a **new Space**, because the existing Space may serve a different app and should not be overwritten blindly.

## 4. Push the dashboard files to that Space

In the project root, substitute your actual new Space name below:

```powershell
git clone https://huggingface.co/spaces/EjazBhai/insurance-policy-rag-evaluation hf-eval-space
Copy-Item eval/hf_space/* hf-eval-space/ -Force
Copy-Item data/eval/questions.json hf-eval-space/questions.json -Force
if (Test-Path eval/results_retrieval.json) { Copy-Item eval/results_retrieval.json hf-eval-space/results_retrieval.json -Force }
if (Test-Path eval/results_generation.json) { Copy-Item eval/results_generation.json hf-eval-space/results_generation.json -Force }
git -C hf-eval-space add .
git -C hf-eval-space commit -m "Deploy Policy RAG evaluation dashboard"
git -C hf-eval-space push
```

Authenticate to Hugging Face when Git prompts you. Use a Hugging Face access token with write access to the new Space; never paste that token into ChatGPT or commit it to a file. If the Space name is different, change the URL and local folder name accordingly.

Space builds can take a few minutes. When it is running, open the Space URL; the app listens on port 7860. If a report wasn't generated locally, the dashboard displays “Not run” instead of inventing a score.

## 5. Updating the displayed metrics

After each evaluation run, copy the new `results_retrieval.json` and/or `results_generation.json` into `hf-eval-space`, commit, and push. Markdown reports are useful for GitHub and review, but the Space dashboard reads the JSON files.

## Important

- The Hugging Face Space only renders stored reports. Evaluation execution stays local, where your index and secret API key are configured.
- LLM-judged groundedness and question relevance are estimates, not human validation or RAGAS scores.
- The current data is LLM-generated from indexed chunks, so it is not a fully independent benchmark.
- The dashboard should not be used as a decision engine for live insurance claims.
