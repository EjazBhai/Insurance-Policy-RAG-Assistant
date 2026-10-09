---
title: Policy RAG Evaluation Lab
emoji: 📊
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Policy RAG Evaluation Lab

A read-only dashboard for retrieval ranking, answer quality, LLM-judged groundedness, evidence availability and latency. It only visualizes saved JSON reports; it does not embed API keys or invoke the generator at public Space runtime.

## Add benchmark results

Copy these generated files from the main repository into this Space repository root after running evaluation locally:

- `eval/results_retrieval.json` → `results_retrieval.json`
- `eval/results_generation.json` → `results_generation.json`
- `data/eval/questions.json` → `questions.json`

Without report files, the page intentionally displays “Not run” rather than example scores.

## Metrics and limitations

The retrieval report compares semantic, hybrid and hybrid + reranking against labelled source+page ground truth. Generation metrics use an LLM-as-judge, not human gold answers. The current evaluation questions were generated from indexed passages and are not a fully independent holdout benchmark. See `Methodology` in the dashboard and the main repository's evaluation notes before interpreting scores.
