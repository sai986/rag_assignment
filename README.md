# RAG Assignment: Baseline Retrieval vs Cross-Encoder Re-Ranking

This repository contains a RAG experiment over the EU Artificial Intelligence Act. It compares a baseline dense bi-encoder retrieval pipeline against a two-stage pipeline that re-ranks dense retrieval candidates with a cross-encoder.

## Files

- `RAG_LMA_Assignment_v1.pdf` - assignment prompt.
- `data/EU_Artificial_Intelligence_Act.pdf` - source document used as the corpus.
- `notebooks/rag_baseline_vs_reranking.ipynb` - main notebook.
- `outputs/pages.csv` - page-level extracted text.
- `outputs/chunks.csv` - retrieval chunks.
- `outputs/baseline_retrieval_results.csv` - top-10 baseline retrieval results.
- `outputs/reranked_results.csv` - cross-encoder re-ranked results.
- `outputs/latency_results.csv` - retrieval and re-ranking latency.
- `outputs/llm_prompts.csv` - baseline and re-ranked prompts for the selected failure queries.
- `report/report.md` - living report draft.
- `PLAN.md` - progress tracker.

## Setup

Install dependencies:

```powershell
py -X utf8 -m pip install -r requirements.txt
```

## Local Models

The model files are not committed to GitHub because they are large. Download them manually from Hugging Face into these folders:

```text
models/all-MiniLM-L6-v2
models/ms-marco-MiniLM-L-6-v2
```

Embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Cross-encoder model:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The notebook is configured to load these models from the local `models/` directory.

## Answer Generation

The notebook exports prompts for the final LLM answer-comparison step. Run the exported prompts through the same LLM and save the answers in:

```text
outputs/llm_answers.csv
```

Do not store API keys or provider credentials in the notebook or repository.

## Current Status

Implemented:

- PDF extraction with PyMuPDF.
- Header/footer cleanup.
- Page-aware continuous chunking.
- Baseline dense retrieval with `all-MiniLM-L6-v2`.
- Cross-encoder re-ranking with `ms-marco-MiniLM-L-6-v2`.
- Initial rank-shift and latency outputs.
- Prompt export and answer generation for selected failure queries.
- Final failure-query analysis and report draft.
