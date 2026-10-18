# RAG Assignment Plan: Baseline Retrieval vs Cross-Encoder Re-Ranking

## Current Status

- [x] Read the assignment PDF.
- [x] Reviewed relevant class material on RAG fundamentals, bi-encoders, cross-encoders, chunking, grounded generation, and retrieval failure modes.
- [x] Selected the corpus: `data/EU_Artificial_Intelligence_Act.pdf`.
- [x] Verified that the selected PDF has 144 pages.
- [x] Verified that text extraction works with PyMuPDF.
- [x] Estimated corpus size: about 115,766 extracted words.
- [x] Created Step 1 notebook for PDF extraction and light cleaning.
- [x] Generated `outputs/pages.csv` with 144 page records.
- [x] Created living report draft at `report/report.md`.
- [x] Updated report with baseline retrieval, cross-encoder re-ranking, rank-shift candidates, and latency.
- [x] Exported final baseline and re-ranked LLM prompts to `outputs/llm_prompts.csv`.
- [x] Added generic answer-template cells to the notebook.
- [ ] Implement the notebook pipeline.
- [ ] Run retrieval and re-ranking experiments.
- [ ] Identify at least two strong failure queries.
- [ ] Generate baseline and re-ranked answers.
- [ ] Measure latency.
- [ ] Write the final report.
- [ ] Prepare GitHub submission.

## Objective

Build a reproducible RAG experiment over the EU Artificial Intelligence Act comparing:

1. Baseline dense retrieval using a bi-encoder.
2. Dense retrieval followed by cross-encoder re-ranking.

The final submission should include a GitHub repository and a concise report showing rank shifts, answer differences, latency, and scaling analysis.

## Proposed Project Structure

```text
rag_assignment/
  data/
    EU_Artificial_Intelligence_Act.pdf
  notebooks/
    rag_baseline_vs_reranking.ipynb
  outputs/
    chunks.csv
    retrieval_results.csv
    latency_results.csv
  report/
    report.md
  requirements.txt
  README.md
  PLAN.md
```

## Phase 1: Corpus Understanding

Status: mostly done.

- [x] Confirm the PDF exists in `data/`.
- [x] Confirm page count.
- [x] Confirm text extraction works.
- [x] Inspect document structure:
  - recitals,
  - definitions,
  - prohibited AI practices,
  - high-risk AI systems,
  - transparency duties,
  - general-purpose AI models,
  - penalties,
  - annexes.
- [x] Decide whether to index the full document or exclude noisy sections.

Design decision: index the full document. Preserve page numbers for citation and debugging. If recitals dominate retrieval too much, note that as an observed behavior rather than changing the main corpus.

Observed structure:

- Pages 1-43: recitals/background and legal motivation.
- Page 44 onward: operative regulation begins with Chapter I, general provisions.
- Page 53 onward: Chapter III, high-risk AI systems.
- Page 88 onward: Chapter VI, measures in support of innovation.
- Page 100 onward: Chapter VIII, EU database for high-risk AI systems.
- Page 101 onward: Chapter IX, post-market monitoring and market surveillance.
- Page 114 onward: Chapter XI, delegation of power and committee procedure.
- Pages 124-144: Annexes I-XIII.

Corpus size estimate:

- 144 pages.
- About 115,766 extracted words.
- Average of about 804 words per page.
- Only 2 pages had fewer than 100 extracted words.

Resolved extraction issue:

- Initial `pypdf` extraction introduced spacing artifacts, for example `ar tif icial`, `syste ms`, `r isk`, and `Ar ticle`.
- Switched to PyMuPDF because it extracts this PDF with normal word spacing.
- Current `clean_text` has no occurrences of the checked artifacts: `REGUL A TION`, `EUR OPEAN`, `ar tif icial`, `syste ms`, `r isk`, or `Ar ticle`.

## Phase 2: Text Extraction and Cleaning

Status: complete for Step 1.

- [x] Extract text page by page using PyMuPDF.
- [x] Store page-level metadata:
  - source file,
  - page number,
  - extracted text.
- [x] Apply light cleaning:
  - collapse repeated whitespace,
  - remove excessive line breaks,
  - normalize common PDF spacing artifacts where safe.
- [x] Avoid aggressive rewriting that could change legal meaning.
- [x] Save extracted page records to `outputs/pages.csv`.
- [x] Remove repeated Official Journal header/footer noise from `clean_text`.

Text cleaning policy:

- Collapse repeated whitespace into a single space.
- Convert line breaks within a page into spaces.
- Remove page footer noise only when it is clearly repeated and not meaningful, such as `OJ L, 12.7.2024` and `ELI: ...`.
- Preserve article numbers, paragraph numbers, annex names, list letters, and legal references.
- Do not remove stop words.
- Do not paraphrase or rewrite extracted text.
- Do not apply broad regular expressions that join arbitrary short tokens, because that could damage legal terms or citations.
- Maintain both `raw_text` and `clean_text` during extraction so cleaning remains auditable.

Design decision: use PyMuPDF extraction with whitespace cleanup and footer removal. No targeted word replacement is currently needed.

Expected page record:

```python
{
    "source": "EU_Artificial_Intelligence_Act.pdf",
    "page": 42,
    "text": "..."
}
```

## Phase 3: Chunking

Status: complete.

- [x] Create chunks from cleaned page text.
- [x] Preserve page ranges for each chunk.
- [x] Use continuous document chunking across page boundaries.
- [x] Use preferred structural split points where possible.
- [x] Use target chunk size around 600 words.
- [x] Use minimum chunk size around 250 words.
- [x] Use maximum chunk size around 900 words.
- [x] Use overlap around 100 words.
- [x] Add lightweight context to each chunk, such as document title and page range.
- [x] Save chunks to `outputs/chunks.csv`.

Expected chunk fields:

```text
chunk_id
text
page_start
page_end
word_count
char_count
```

Chunking design:

1. Load `outputs/pages.csv`.
2. Use `clean_text`, not `raw_text`.
3. Treat pages as ordered metadata, not hard chunk boundaries.
4. Concatenate pages into one continuous document stream with a single space between pages.
5. Preserve each word's source page so every chunk can report `page_start` and `page_end`.
6. Prefer structural split points:
   - `CHAPTER ...`
   - `SECTION ...`
   - `Article ...`
   - `ANNEX ...`
   - numbered clauses such as `1.`
   - legal list items such as `(a)`, `(b)`, `(i)`, `(ii)`
7. Accumulate structural units until the target size.
8. Close a chunk before exceeding the maximum size.
9. If a structural unit is larger than the maximum size, split it with word windows.
10. Add overlap between chunks, including across page boundaries.

Rationale: legal documents often continue clauses across page boundaries. Page-aware continuous chunking preserves continuity while still allowing citations through page ranges. Overlap reduces split-fact failures, especially for definitions, exceptions, and conditions.

Chunking result:

- Word stream length: 90,406 words.
- Structural units detected: 1,968.
- Chunks created: 168.
- Minimum chunk size: 398 words.
- Maximum chunk size: 812 words.
- Mean chunk size: about 638 words.
- Chunks below 250 words: 0.
- Chunks above 900 words: 0.
- Page-spanning chunks: 143.

## Phase 4: Baseline Bi-Encoder Retrieval

Status: complete for initial candidate queries.

- [x] Choose embedding model.
- [x] Embed all chunks once.
- [x] Embed each query.
- [x] Compute cosine similarity.
- [x] Retrieve top 10 chunks.
- [ ] Use the top 3 chunks directly for baseline answer generation.

Recommended embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Actual embedding setup:

- Model: `sentence-transformers/all-MiniLM-L6-v2`.
- Loaded from local path: `models/all-MiniLM-L6-v2`.
- Embedding dimension: 384.
- Chunk embeddings saved to `outputs/chunk_embeddings.npy`.
- Initial baseline retrieval results saved to `outputs/baseline_retrieval_results.csv`.
- Initial query set: 8 candidate queries, top 10 chunks per query.

Alternative:

```text
BAAI/bge-small-en-v1.5
```

Design decision: use NumPy cosine similarity instead of FAISS because this is a small corpus.

## Phase 5: Cross-Encoder Re-Ranking

Status: complete for initial candidate queries.

- [x] Choose cross-encoder model.
- [x] Take the top 10 baseline candidates.
- [x] Score all `(query, chunk)` pairs.
- [x] Sort candidates by cross-encoder score.
- [x] Select top 3 re-ranked chunks.
- [ ] Use the same LLM prompt format as the baseline pipeline.

Recommended re-ranker:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

Actual re-ranking setup:

- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- Loaded from local path: `models/ms-marco-MiniLM-L-6-v2`.
- Re-ranked 8 candidate queries with 10 baseline candidates per query.
- Re-ranked results saved to `outputs/reranked_results.csv`.
- Latency results saved to `outputs/latency_results.csv`.
- Mean baseline retrieval time: about 0.010 seconds per query.
- Mean cross-encoder re-ranking time: about 1.42 seconds per query for 10 candidates.
- Re-ranked top 3 included chunks originally ranked as low as baseline rank 10.

Rationale: bi-encoder is fast and suitable for recall; cross-encoder is slower but more precise on a shortlist.

## Phase 6: Prompt Design

Status: complete for prompt export.

- [x] Use one fixed prompt template for both pipelines.
- [x] Number retrieved passages as `[S1]`, `[S2]`, `[S3]`.
- [x] Require citations after factual claims.
- [x] Include a refusal clause when passages do not answer the question.
- [x] Export baseline and re-ranked prompts for the two selected failure queries.

Draft prompt:

```text
Answer using only the numbered passages below.
If the passages do not contain the answer, say that the document does not provide enough information.
Cite every factual claim using passage ids like [S1], [S2].

Context:
[S1] ...
[S2] ...
[S3] ...

Question: ...
```

## Phase 7: Query Design

Status: not started.

- [ ] Create 8-10 candidate queries.
- [ ] Run baseline retrieval and re-ranking for each query.
- [ ] Select at least two failure queries where baseline retrieval degrades but re-ranking improves relevance.
- [ ] Prefer cases where a relevant chunk appears in baseline ranks 4-10 and moves into top 3 after re-ranking.

Candidate query categories:

1. Prohibited AI practices.
2. Biometric identification exceptions.
3. High-risk AI systems in education or employment.
4. Transparency obligations for AI interaction.
5. Deep fake disclosure.
6. General-purpose AI model obligations.
7. Systemic-risk GPAI model criteria.
8. Penalties for non-compliance.
9. Scope exclusions.
10. Law enforcement exceptions.

Good failure pattern:

```text
Relevant chunk appears in baseline rank 4-10.
Cross-encoder moves it into rank 1-3.
Baseline answer misses or misstates a detail.
Re-ranked answer includes the correct clause.
```

## Phase 8: Evaluation Tables

Status: not started.

- [ ] Record baseline retrieval results.
- [ ] Record cross-encoder re-ranking results.
- [ ] Record rank shifts for selected failure queries.
- [ ] Record latency for baseline retrieval and re-ranking pipeline.
- [ ] Save results to `outputs/retrieval_results.csv` and `outputs/latency_results.csv`.

Retrieval result fields:

```text
query
pipeline
rank
chunk_id
page_start
page_end
bi_encoder_score
cross_encoder_score
is_relevant
notes
```

Latency result fields:

```text
query
baseline_retrieval_seconds
reranking_seconds
total_reranking_pipeline_seconds
```

## Phase 9: Answer Generation

Status: not started.

- [ ] Choose answer-generation LLM.
- [ ] Generate Answer 1 using baseline top 3 chunks.
- [ ] Generate Answer 2 using re-ranked top 3 chunks.
- [ ] Use the exact same prompt template for both answers.
- [ ] Compare whether Answer 1:
  - hallucinates,
  - omits an important exception,
  - cites weak evidence,
  - gives a generic answer,
  - misstates a rule.
- [ ] Compare whether Answer 2 improves grounding and specificity.

Possible LLM choices:

- Gemini API.
- OpenAI API.
- Ollama local model.

Design decision: retrieval and re-ranking are the core assignment; answer-generation LLM choice is secondary as long as the prompt is identical.

Actual answer-generation setup:

- Prompts are exported to `outputs/llm_prompts.csv`.
- Answer template is created at `outputs/llm_answers.csv`.
- The same LLM and decoding settings should be used for both baseline and re-ranked prompts.
- API keys or provider credentials should not be stored in the notebook or repository.
- Current status: answer generation still needs to be run with the chosen LLM before final report completion.

## Phase 10: Report

Status: started.

The report should be concise and in our own words.

Suggested structure:

1. Document and setup.
2. Architecture comparison.
3. Failure query analysis.
4. Qualitative answer comparison.
5. Latency profiling.
6. Scaling question.
7. Short conclusion.

Required content:

- [ ] Explain bi-encoder vs cross-encoder.
- [ ] Show at least two failure queries.
- [ ] Show rank shifts, such as chunk moving from rank 8 to rank 1.
- [ ] Compare Answer 1 and Answer 2.
- [ ] Include latency table.
- [ ] Explain why cross-encoders are not run over the whole document collection from the start.
- [x] Record document choice, extraction decision, header/footer cleanup, and chunking strategy.
- [x] Add initial architecture comparison.
- [x] Add initial rank-shift table.
- [x] Add initial latency summary.
- [x] Add scaling explanation draft.

## Phase 11: GitHub Submission

Status: not started.

- [ ] Ensure notebook runs top to bottom.
- [ ] Add `requirements.txt`.
- [ ] Add `README.md` with setup/run instructions.
- [ ] Add generated output tables or include them in the notebook.
- [ ] Add final report.
- [ ] Push to public or shared GitHub repository.

## Implementation Order

When implementation begins, proceed in this order:

1. Create project folders and requirements.
2. Build PDF extraction and cleaning.
3. Build chunking and save chunks.
4. Build bi-encoder retrieval.
5. Build cross-encoder re-ranking.
6. Add prompt formatting.
7. Add answer generation.
8. Add latency measurement.
9. Run candidate queries.
10. Select final failure queries.
11. Write report.
12. Prepare GitHub submission.

## Open Decisions

- [ ] Which answer-generation LLM should be used?
- [ ] Whether to use `all-MiniLM-L6-v2` or `bge-small-en-v1.5` for embeddings.
- [ ] Whether to write the final report as Markdown or directly in a notebook section.
- [ ] Whether to include only final selected failure queries or all candidate query results.
- [x] Whether to index the full document or only pages 44-144 plus selected recitals.
- [ ] Revisit chunk size after retrieval testing. Current output has 168 chunks with about 638 words on average; if retrieval is too broad or answer context is noisy, try smaller chunks around 400 target words and 650 max words.

## Next Design Decisions Before Coding

Recommended choices:

- Index the full document. If too many recital chunks dominate retrieval, discuss that as part of the analysis or run a secondary diagnostic, but keep the main experiment on the full corpus.
- Use `BAAI/bge-small-en-v1.5` for embeddings if dependency download works; otherwise use `sentence-transformers/all-MiniLM-L6-v2`.
- Use `cross-encoder/ms-marco-MiniLM-L-6-v2` for re-ranking.
- Use simple NumPy cosine similarity instead of FAISS.
- Write the report in Markdown and export to PDF at the end if needed.
- Keep all candidate query results in the notebook, but include only the best 2-3 failure cases in the report.
