# Baseline Retrieval vs Cross-Encoder Re-Ranking for RAG

## 1. Document and Setup

This experiment uses the **EU Artificial Intelligence Act** as the source document. I chose this document because it is long, text-heavy, and rule-based. It contains definitions, obligations, exceptions, prohibited practices, high-risk AI categories, transparency duties, penalties, and annexes. These characteristics make it suitable for testing retrieval failures in a RAG pipeline.

The PDF has 144 pages. Text was extracted page by page and each page number was preserved so that retrieved chunks can be traced back to the original document.

### Extraction Notes

The first extraction attempt used `pypdf`, but it produced spacing artifacts in many words. For example, the visible PDF text:

```text
REGULATION (EU) 2024/1689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL
```

was extracted as:

```text
REGUL A TION (EU) 2024/1689 OF THE EUR OPEAN P ARLIAMENT AND OF THE CO UNCIL
```

This would hurt retrieval because important terms such as `artificial`, `systems`, `risk`, and `Article` could be split incorrectly. I switched to PyMuPDF, which extracted the same pages with normal word spacing.

Repeated page header and footer text, such as publication metadata and page markers, was removed from the cleaned text because it does not help answer user questions and would add noise to embeddings. Legal citations that are part of the document text were kept.

## 2. Chunking Strategy

I used the full document rather than filtering out the recital section. Pages were treated as metadata, not as hard chunk boundaries.

The chunking process was:

1. Extract cleaned text for each page.
2. Concatenate pages into a continuous document stream.
3. Preserve each word's source page number.
4. Prefer legal structure boundaries such as `CHAPTER`, `SECTION`, `Article`, `ANNEX`, numbered clauses, and list items.
5. Build chunks with target size around 600 words.
6. Enforce a maximum chunk size around 900 words.
7. Add 100-word overlap between chunks, including across page boundaries.

The current chunking output is:

| Metric | Value |
|---|---:|
| Total words | 90,406 |
| Structural units detected | 1,968 |
| Chunks created | 168 |
| Minimum chunk size | 398 words |
| Maximum chunk size | 812 words |
| Mean chunk size | 637.5 words |
| Chunks below 250 words | 0 |
| Chunks above 900 words | 0 |
| Page-spanning chunks | 143 |

This chunking setup is intentionally conservative. Legal rules often include conditions and exceptions, so larger chunks help preserve enough context. If later retrieval results are too broad or noisy, I will revisit this setting and test smaller chunks.

## 3. Architecture Comparison

A bi-encoder embeds the query and each chunk independently. Since the chunk embeddings do not depend on the query, they can be computed once and reused. At query time, only the query embedding is computed, and chunks are ranked using cosine similarity.

A cross-encoder reads the query and candidate chunk together. This is more expensive because the model must run once for every `(query, chunk)` pair. The advantage is that the model can compare the query and chunk directly through token-level attention. In this assignment, I use the cross-encoder only after the bi-encoder has produced a shortlist of 10 candidates.

## 4. Retrieval Pipelines

Both pipelines use the same chunk corpus. The only difference is whether the top 10 dense-retrieval candidates are used directly or re-ranked before selecting the final top 3 context chunks.

### Pipeline 1: Baseline Retrieval

The baseline retrieval pipeline uses a dense bi-encoder. I used `sentence-transformers/all-MiniLM-L6-v2`, loaded from a local folder because direct model download from Hugging Face was blocked by the local network/certificate setup.

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Embedding dimension: 384
- Similarity function: cosine similarity
- Number of candidates retrieved: top 10
- Number of chunks to be sent to the LLM: top 3
- Chunk embeddings file: `outputs/chunk_embeddings.npy`
- Baseline retrieval output: `outputs/baseline_retrieval_results.csv`

### Pipeline 2: Advanced Re-Ranking

The advanced pipeline starts from the same top 10 baseline candidates. It then scores each `(query, chunk)` pair with a cross-encoder and sorts the candidates by the cross-encoder score.

- Initial candidates: top 10 from baseline dense retrieval
- Cross-encoder model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Model source: local folder `models/ms-marco-MiniLM-L-6-v2`
- Re-ranked chunks to be sent to LLM: top 3
- Re-ranked output: `outputs/reranked_results.csv`
- Latency output: `outputs/latency_results.csv`
- Prompt output: `outputs/llm_prompts.csv`
- Prompt structure: same prompt is used for baseline and re-ranked answer generation
- Answer output: `outputs/llm_answers.csv`

Initial re-ranking over 8 candidate queries showed that the cross-encoder sometimes promoted chunks originally ranked outside the baseline top 3. In the current run, some chunks in the re-ranked top 3 originally appeared at baseline ranks 4, 5, 6, 7, and 10.

The answer-generation prompt template is:

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

The same template is used for both pipelines. Only the three retrieved passages change.

The full prompts used for the selected failure queries are saved in `outputs/llm_prompts.csv`, and the generated answers are saved in `outputs/llm_answers.csv`. I keep the report focused on the rank shifts and answer differences rather than pasting the full prompt and full answer text for every case.

## 5. Failure Query Analysis

This section records retrieval-level rank shifts and compares the answers generated from the baseline and re-ranked contexts.

### Candidate Rank Shifts

| Query | Chunk | Baseline Rank | Re-ranked Rank | Page Range | Shift |
|---|---|---:|---:|---|---:|
| What obligations apply to providers of general-purpose AI models with systemic risk? | C0070 | 10 | 3 | 41-42 | +7 |
| What criteria are used to designate general-purpose AI models with systemic risk? | C0119 | 10 | 3 | 86-87 | +7 |
| What obligations apply to providers of general-purpose AI models with systemic risk? | C0119 | 7 | 1 | 86-87 | +6 |
| What transparency obligations apply when users interact with an AI system? | C0014 | 7 | 2 | 7-8 | +5 |
| What penalties apply for non-compliance with prohibited AI practices? | C0015 | 6 | 2 | 8-8 | +4 |
| Which AI practices are prohibited because they manipulate a person's behaviour? | C0030 | 6 | 3 | 17-17 | +3 |
| When can law enforcement use real-time remote biometric identification in public spaces? | C0020 | 6 | 3 | 11-11 | +3 |
| What criteria are used to designate general-purpose AI models with systemic risk? | C0116 | 5 | 2 | 83-84 | +3 |

The strongest early candidates are the general-purpose AI/systemic-risk queries because relevant chunks moved from ranks 7 and 10 into the re-ranked top 3. These are useful because the baseline top 3 would not include all of those promoted chunks.

### Failure Query 1

Question:

What obligations apply to providers of general-purpose AI models with systemic risk?

Why this query is difficult:

The document has several nearby topics around general-purpose AI models: definitions, copyright/training summaries, systemic-risk classification, provider duties, and downstream documentation. A dense retriever can retrieve semantically related general-purpose AI chunks without necessarily ranking the specific obligations highest.

Rank shift:

| Chunk | Baseline Rank | Re-ranked Rank | Page Range | Reason |
|---|---:|---:|---|---|
| C0119 | 7 | 1 | 86-87 | Promoted to the top by the cross-encoder for the systemic-risk obligations query. |
| C0070 | 10 | 3 | 41-42 | Moved into the re-ranked top 3 despite being last in the baseline top 10. |

Answer comparison:

| Pipeline | Observation |
|---|---|
| Baseline context | Uses chunks C0052, C0050, C0053. |
| Re-ranked context | Uses chunks C0119, C0053, C0070. |
| Baseline answer | The answer covered risk mitigation, model evaluation, cybersecurity, incident reporting, and general systemic-risk duties. It was useful, but it mainly relied on recital/background chunks and did not clearly separate direct obligations from supporting explanation. |
| Re-ranked answer | The answer was more focused on provider obligations and compliance mechanisms. It included risk assessment and mitigation, incident reporting, cybersecurity, codes of practice, harmonised standards, and alternative means of demonstrating compliance. |

Short generated-answer comparison:

- Baseline answer: emphasised risk mitigation, model evaluations, cybersecurity protection, incident reporting, and general obligations.
- Re-ranked answer: retained the main obligations but added clearer compliance mechanisms such as codes of practice, harmonised standards, and alternative means of demonstrating compliance.

Observation: re-ranking improved the context by moving C0119 from baseline rank 7 to rank 1 and C0070 from baseline rank 10 to rank 3. The generated answer became more specific about compliance routes and obligations rather than only summarising background rationale.

### Failure Query 2

Question:

When can law enforcement use real-time remote biometric identification in public spaces?

Why this query is difficult:

This query depends on conditions and exceptions. The relevant evidence is spread across recitals and operative provisions, including strict necessity, authorisation, fundamental rights assessment, national rules, and permitted objectives. Dense retrieval found related biometric chunks, but re-ranking changed which specific condition chunks were placed in the top 3.

Rank shift:

| Chunk | Baseline Rank | Re-ranked Rank | Page Range | Reason |
|---|---:|---:|---|---|
| C0083 | 4 | 2 | 52-53 | Contains operative authorisation and assessment requirements; promoted into top 3. |
| C0020 | 6 | 3 | 11-11 | Contains Member State authorisation/national-law condition; promoted into top 3. |

Answer comparison:

| Pipeline | Observation |
|---|---|
| Baseline context | Uses chunks C0019, C0017, C0045. |
| Re-ranked context | Uses chunks C0019, C0083, C0020. |
| Baseline answer | The answer correctly listed permitted situations, authorisation, urgency handling, scope limits, impact assessment, and national-law requirements. However, one baseline top-3 chunk was about post-remote biometric identification rather than the real-time public-space use asked in the query. |
| Re-ranked answer | The answer focused more tightly on real-time remote biometric identification in publicly accessible spaces. It included fundamental-rights assessment, EU database registration, prior authorisation, urgency exceptions, national-law permission, and notifications. |

Short generated-answer comparison:

- Baseline answer: gave a broadly correct answer, but mixed in less central context about post-remote biometric identification.
- Re-ranked answer: more directly addressed real-time use in public spaces and included the operational conditions promoted by re-ranking: prior authorisation, urgency handling, EU database registration, notifications, and Member State national-law permission.

Observation: re-ranking promoted C0083 from baseline rank 4 to rank 2 and C0020 from baseline rank 6 to rank 3. This replaced less central baseline context with chunks that directly addressed authorisation, registration, urgency exceptions, and Member State national-law conditions.

## 6. Latency Profiling

Initial latency over 8 candidate queries:

| Measurement | Baseline Retrieval Time | Re-ranking Time | Total Re-ranking Pipeline Time |
|---|---:|---:|---:|
| Mean over 8 candidate queries | 0.010 s | 1.419 s | 1.429 s |
| Minimum | 0.009 s | 1.326 s | 1.336 s |
| Maximum | 0.012 s | 1.580 s | 1.591 s |

For the two selected failure queries:

| Query | Baseline Retrieval Time | Re-ranking Time | Total Re-ranking Pipeline Time |
|---|---:|---:|---:|
| GPAI systemic-risk obligations | 0.012 s | 1.624 s | 1.637 s |
| Real-time biometric identification by law enforcement | 0.013 s | 1.514 s | 1.527 s |

For the two selected failure queries, the prompts have been exported to `outputs/llm_prompts.csv`. The notebook also creates an `outputs/llm_answers.csv` template. The same LLM and decoding settings should be used for both the baseline and re-ranked prompts. API keys or provider credentials should not be stored in the notebook, report, or repository.

## 7. Scaling Question

We do not run a cross-encoder over the entire collection from the start because the cross-encoder must process each query and chunk together. Its score depends on the interaction between the query tokens and the chunk tokens, so the document-side computation cannot be fully precomputed in the same way as bi-encoder embeddings.

The practical pattern is therefore two-stage retrieval. First, the bi-encoder cheaply searches the full chunk collection and produces a candidate set with good recall. Then the cross-encoder spends more compute on only that shortlist to improve precision. In this experiment, dense retrieval over 168 chunks took about 0.010 seconds per query, while cross-encoder re-ranking of only 10 candidates took about 1.419 seconds per query.

## 8. Conclusion

The two-stage pipeline improved precision on the selected difficult queries. Dense retrieval was very fast and usually found relevant material somewhere in the top 10, but important chunks could remain outside the top 3. Cross-encoder re-ranking added about 1.5 seconds per query for 10 candidates, but it promoted more directly useful chunks into the context sent to the LLM. The result was stronger grounding for queries involving systemic-risk obligations and law-enforcement exceptions.
