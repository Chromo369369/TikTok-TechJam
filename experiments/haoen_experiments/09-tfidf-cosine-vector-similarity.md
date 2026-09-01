---
experiment: "09"
title: "TF-IDF cosine similarity: closing the "vector similarity" gap"
type: experiment
technical_score: 0.945456
delta: +0.0035
decision: "Adopted"
summary: "Pure-stdlib TF-IDF cosine closing the vector-similarity gap"
source: "REPORT.md"
---
# TF-IDF cosine similarity: closing the "vector similarity" gap

`problem.md` (the underlying hackathon brief) specifies a hybrid retrieval pipeline combining "keyword, category, and vector similarity" -- the agent had the first two (BM25, the category index) but nothing resembling the third; retrieval and ranking were entirely lexical/exact-match. Embeddings and a real vector index are out of scope by the brief's own constraints ("must run entirely in-memory for light execution", no external services required), so the agent now computes a lightweight, pure-stdlib TF-IDF cosine-similarity signal instead: at index time, a first pass over the catalog computes document frequencies (`_document_frequencies`), from which every product gets a sparse TF-IDF vector (`_tfidf_vector`, capped at the 40 highest-weight terms for memory/speed); the customer's full cumulative message text (`state.message_history`, tracked across all turns) gets the same treatment each turn, and cosine similarity between the two (`_tfidf_cosine`) becomes a 22nd feature, `tfidf_cosine`.

This is a real, independent signal, not a relabeling of what the phrase index already does: the phrase index only fires on an *exact* cleaned constraint string, while TF-IDF cosine picks up partial/fuzzy lexical overlap across the entire conversation, including the customer's free-form category phrasing and any leftover words the structured lexicons don't specifically parse. It's also the agent's best available hedge against the paraphrasing risk flagged earlier (`docs/competition_specification.md`): if the private simulator ever stops disclosing verbatim substrings, this is the one signal that degrades gracefully instead of going to zero.

Refit with this feature (same target-product-disjoint 5-fold protocol): ranking-gate rank-1 count rose 61→74/200 with MRR 0.424→0.532 (paired delta +0.108, bootstrap 95% CI [+0.055, +0.162], 106 improved / 43 worsened / 51 unchanged), and the fitted `tfidf_cosine` weight (+0.70) is positive and comparable in magnitude to the other mid-tier features -- a real, non-trivial contributor, not dead weight. End-to-end: Hit Rate@10 stayed at 1.000, MRR rose 0.891 → 0.901, MTTC eased slightly to 2.245, for a technical score of **0.945456**, confirmed by a strict OOF refit at **0.943681** (up from v2's OOF 0.940179 -- another genuinely generalizing gain, not a same-data artifact).
