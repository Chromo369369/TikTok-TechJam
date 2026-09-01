# TechJam Shopping Copilot

An offline, multi-turn conversational shopping agent for the **TechJam Conversational E-Commerce Search Challenge**. Given an anonymized shopper profile and a sequence of messages, the agent asks useful follow-up questions and recommends products from a frozen catalog. Its goal is to place the shopper's hidden target product in the Top 10 as early and as highly ranked as possible.

The shipped system is deterministic, uses no network calls or third-party APIs at runtime, and relies only on Python's standard library. It pairs catalog retrieval and constraint tracking with Monte Carlo look-ahead to decide both what to ask and how many recommendations to show on a turn.

> **Submission summary:** This repository contains source code, a local evaluator, public development data, a reproducible demo tracer, methodology records, and the information needed for a Devpost project description and public GitHub submission. Add the public repository URL and public demo-video URL before submitting.

## Table of contents

- [Challenge and problem](#challenge-and-problem)
- [Solution overview](#solution-overview)
- [How the agent works](#how-the-agent-works)
- [Results and evaluation](#results-and-evaluation)
- [Repository guide](#repository-guide)
- [Setup](#setup)
- [Run and reproduce](#run-and-reproduce)
- [Demo video and Devpost checklist](#demo-video-and-devpost-checklist)
- [Technology, APIs, data, and assets](#technology-apis-data-and-assets)
- [Limitations and future work](#limitations-and-future-work)
- [Team contributions](#team-contributions)
- [Data use and security](#data-use-and-security)

## Challenge and problem

The challenge provides a frozen 50,000-product catalog from the `Clothing_Shoes_and_Jewelry` category of Amazon Reviews 2023, plus 200 labeled public sessions for development. The final organizer evaluation uses additional private sessions that are not included in this repository.

For each session, the evaluator calls `reset(session_id, user_profile)` and then sends a customer message. On each of up to 10 turns, the agent may:

- return a natural-language question and one structured `ask_attribute`; and/or
- return an ordered list of up to 10 catalog `parent_asin` values.

A session succeeds when the hidden target product appears in the valid scored Top 10. Only exact `parent_asin` matches count. The public set covers four behaviors: Buying (40%), Browsing (40%), Intent Override (15%), and Boundary cases (5%). The agent sees only a safe aggregate profile; it never sees raw user IDs, purchase history, free-text reviews, hidden intent cards, scenario labels, or private targets at runtime.

The official score combines retrieval success, ranking quality, and speed:

```text
HitRate@10 = successful sessions / N
MRR        = mean reciprocal rank of the target (0 for a miss)
MTTC       = mean first-hit turn (11 for a miss)
Efficiency = clip((11 - MTTC) / 10, 0, 1)

TechnicalScore = 0.50 * HitRate@10 + 0.30 * MRR + 0.20 * Efficiency
```

## Solution overview

Shopping Copilot treats the interaction as a partially observable decision problem rather than as a sequence of independent searches. A recommendation shown too early can end a session at a weak rank; holding back a weakly supported candidate and asking the right question can yield a much better-ranked hit on the next turn. The agent therefore jointly plans clarification and recommendation-list length.

The solution addresses the problem through four connected capabilities:

1. **Conversation memory and intent updates.** It accumulates evidence from each message, tracks previously asked questions and shown products, and handles a change in shopper intent without permanently over-weighting stale information.
2. **Catalog-grounded retrieval.** It searches only the permitted product metadata, combining lexical evidence, structured attributes, product-category phrases, brand/store signals, budget cues, and distinctive specification wording.
3. **Adaptive clarification.** It models possible answers to the allowed attributes and evaluates which question is expected to improve the session outcome, while accounting for whether an answer is likely to be useful.
4. **Decision-aware publishing.** It selects how many products to recommend alongside a question. This protects the shopper experience and the score from locking in a low-rank conversion when the current belief is uncertain.

## How the agent works

```text
shopper message + aggregate profile
              |
              v
  extract constraints, phrases, and intent changes
              |
              v
  rank catalog candidates with lexical + metadata evidence
              |
              v
  build a belief over the current candidate set
              |
              +----------------------------+
              |                            |
              v                            v
simulate permitted questions       evaluate list lengths
              |                            |
              +-------------+--------------+
                            v
       return one structured question and ranked ASINs
```

### Evidence extraction and retrieval

The agent builds an in-memory SQLite index from the downloaded catalog. It extracts or recognizes:

- product category and category-path phrases;
- material, color, size, style, brand/store, budget, use case, and feature evidence;
- terms and contiguous phrases from the dialogue;
- exact or near-exact product specification text present in catalog metadata; and
- safe `preference_tags` from the aggregate user profile as soft routing signals.

Candidates are scored using catalog-only signals. The ranking includes BM25-style lexical relevance, phrase matches, structured constraint compatibility, category specificity, and lightweight catalog priors such as rating count, price availability, metadata richness, and average rating. Previously shown products are suppressed on later turns because a continued session proves they were not the target.

### Planning questions and recommendations

The agent maintains a weighted belief over a working candidate set. For each legal structured question (`category`, `material`, `color`, `size`, `style`, `brand`, `budget`, `feature`, `use_case`, or `other`), it simulates answer paths over catalog-derived candidate values. It uses common random numbers across alternatives to make comparisons stable at a practical rollout budget.

It then compares the best clarification action with remaining silent and evaluates multiple possible recommendation-list lengths. The response contains the selected natural-language prompt, its machine-readable `ask_attribute`, ordered recommendations, and zero token usage because the shipped system makes no model/API call.

### Robustness and policy boundaries

The default configuration deliberately treats `other` as a weak, generic open question. `TECHJAM_EVALUATOR_MODE=1` enables a quarantined comparison mode calibrated to the released public simulator's unusually informative `other` behavior. It is not the default because it is evaluator-specific and may not generalize to a private or real-user setting.

The agent is deterministic for a fixed catalog and interaction sequence. It does not access network services, hidden labels, targets, scenario types, or non-catalog private data at runtime.

## Results and evaluation

**E061 Phrase Matching is the final reported configuration.** It adds contiguous two-to-four-word shopper phrases to the existing token-based retrieval signal, allowing the agent to distinguish a product that contains a phrase such as “machine washable” from one that merely contains the same words separately. All other planner, retrieval, constraint, and publishing components remain unchanged from the preceding E060 configuration.

The following are measured on the 200-session public development set, not a claim about the organizer's private evaluation.

| Configuration | Public set | HitRate@10 | MRR | MTTC | Technical score |
| --- | ---: | ---: | ---: | ---: | ---: |
| **E061 final default: phrase matching** | 200 sessions | **0.995000** | **0.980208** | **2.660000** | **0.958363** |
| E060 baseline: no phrase feature | 200 sessions | 0.995000 | 0.967917 | 2.805000 | 0.951775 |
| E061, always show 10 rows | 200 sessions | - | 0.640 | - | 0.875950 |
| E061 evaluator-specific comparison mode | 200 sessions | 0.995000 | 0.980375 | 2.390000 | 0.963813 |

E061 improves the final public technical score by `+0.006588` over E060 while preserving hit rate. It increases MRR and reduces time to conversion without adding an MTTC-specific rule: more precise phrase-level ranking means the agent can correctly publish a top candidate earlier. In the measured full run, 195 of 200 sessions convert at rank 1; the remaining outcomes are one hit each at ranks 2, 4, 6, and 8, plus one miss.

The phrase-weight selection was tested across multiple seeds. The shipped configuration is the strongest measured seed (`0.958363`); the five-seed mean is `0.952278` with standard deviation `0.005418`. The latter is the more conservative estimate for an unseen split.

The comparison with always showing 10 illustrates why list-length planning matters: broad publishing often locks in an inferior rank. The default route favors a generalizable catalog-only question model; the optional evaluator mode is documented only as an analysis control because its remaining advantage is tied to the released simulator's behavior for `other` questions.

See [E061_phrase_matching.md](experiments/E061_phrase_matching.md) for the final experiment record, including split metrics, ablations, seed robustness, and failure taxonomy. [TECHJAM_PROJECT_DOSSIER.md](TECHJAM_PROJECT_DOSSIER.md) preserves an earlier experiment narrative; its historical results should not be mixed with E061 without re-running the relevant configuration.

## Repository guide

```text
starter/agent.py                  submitted Agent implementation
evaluator/local_evaluator.py      deterministic public-set simulator and scorer
data/public_set.jsonl             200 labeled public development sessions
data/catalog.jsonl                downloaded catalog (not committed)
demo/trace_session.py             read-only single-session decision tracer
tests/test_evaluator.py           evaluator unit tests
docs/competition_specification.md task protocol and scoring contract
docs/agent_api_contract.json      machine-readable response contract
docs/submission_rules.md          packaging and reproducibility rules
experiments/                      experiment notes and archived diagnostics
experiments/E061_phrase_matching.md final experiment record and reported result
TECHJAM_PROJECT_DOSSIER.md        detailed project narrative and evidence
DATA_ATTRIBUTION.md               source-data attribution and use requirements
```

## Setup

### Requirements

- Python 3.10 or later
- A copy of `catalog.jsonl.gz` from this repository's GitHub Release
- Approximately enough local disk space to decompress the 50,000-row catalog

No package installation is needed for the shipped agent: it uses the Python standard library only. In particular, it uses `sqlite3` from the standard library to create its in-memory index.

### Download the catalog

The catalog is intentionally excluded from version control. Download `catalog.jsonl.gz` from the GitHub Release associated with this repository, verify it against the release's `SHA256SUMS`, and place the decompressed file at `data/catalog.jsonl`.

```bash
gzip -dk catalog.jsonl.gz
mv catalog.jsonl data/catalog.jsonl
```

The expected catalog size is 50,000 rows. Do not commit the catalog, generated results, API keys, private evaluation data, or release-only artifacts.

## Run and reproduce

### 1. Run the local evaluator

From the repository root, after placing the catalog in `data/catalog.jsonl`:

```bash
python3 -m evaluator.local_evaluator
```

This runs the official-style local evaluator against `data/public_set.jsonl`, prints aggregate and scenario metrics, and writes `results.json` (ignored by Git).

To use paths outside their defaults:

```bash
python3 -m evaluator.local_evaluator \
  --catalog /path/to/catalog.jsonl \
  --dataset data/public_set.jsonl \
  --output results.json
```

### 2. Trace one session end to end

The tracer observes an actual evaluator session without modifying the agent or evaluator. It shows the dialogue, extracted clues, candidate narrowing, and the planner's question/list-length comparison.

```bash
python3 demo/trace_session.py --session public_0007
```

To find an automatically selected illustrative session:

```bash
python3 demo/trace_session.py --find
```

### 3. Run the tests

```bash
python3 -m unittest discover -s tests -v
```

### 4. Optional analysis control

This configuration is for released-simulator analysis only, not the shipped default policy:

```bash
TECHJAM_EVALUATOR_MODE=1 python3 -m evaluator.local_evaluator
```

For a reproducible reported result, record the Git commit, Python version, catalog release/checksum, command, environment variables, and generated `results.json`. The evaluation is deterministic for a fixed input bundle.

## Demo video and Devpost checklist

The competition deliverables call for a written project description, a public code repository, and a short publicly visible YouTube demo linked from Devpost. Use the following before final submission.

### Public repository checklist

- [ ] Make the GitHub/code repository public and add its URL here: `REPLACE_WITH_PUBLIC_REPOSITORY_URL`
- [x] Include readable source for the agent, evaluator, tests, and demo tracer.
- [x] Include this README with project overview, setup, reproduction, limitations, and contribution section.
- [x] Document data attribution and restrictions in [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).
- [ ] Confirm that no `.env`, API key, private data, organizer-only files, or generated results are committed.


### Devpost written-description checklist

Include the following in the Devpost entry:

- **Problem and solution:** explain that the agent improves multi-turn product discovery by retaining constraints, retrieving from catalog metadata, asking high-value questions, and avoiding premature low-rank recommendations.
- **Development tools:** Python 3.10+, standard-library `sqlite3`, command-line tooling, and the local evaluator/test suite. Add editor/notebook tools actually used by the team, if any.
- **APIs:** none at runtime. The default submission has no LLM, cloud, mapping, or external web API dependency.
- **Libraries/frameworks:** Python standard library only (`sqlite3`, `json`, `math`, `random`, `re`, and related modules); no external framework is required.
- **Datasets/assets:** Amazon Reviews 2023 product metadata, selected `Clothing_Shoes_and_Jewelry` catalog, plus the organizer-provided public session set. See [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md).
- **Model/cost disclosure:** no model credentials, API calls, token cost, or external inference cost. The response reports `0` prompt and completion tokens. The agent requires local CPU and memory only.
- **Fallback/network disclosure:** network access is not required. There is no credentialed external-service fallback.

## Technology, APIs, data, and assets

| Area | Used in this project |
| --- | --- |
| Language | Python 3.10+ |
| Runtime dependencies | Python standard library only |
| Storage/search | In-memory SQLite index via `sqlite3`; lexical and structured catalog retrieval |
| ML/decision method | Deterministic Monte Carlo look-ahead with catalog-derived self-play priors |
| External APIs | None at runtime |
| LLM usage | None in the shipped agent |
| Token usage | `0` prompt tokens and `0` completion tokens per response |
| Network requirement | None |
| Dataset | Amazon Reviews 2023 / McAuley Lab UCSD, Clothing/Shoes/Jewelry metadata |
| Assets | Text and structured product metadata; no images, videos, account credentials, or private holdout data |

## Validation approach

During development, we used controlled tests to challenge the system rather than relying only on an aggregate benchmark score. These included message-phrasing perturbations, catalog-field ablations, checks for evaluator-specific behavior, and reproducibility checks.

These tests informed the final design: the default policy prioritizes catalog-grounded evidence and keeps simulator-specific strategies out of the production path. They also establish important boundaries on our claims. Performance depends on metadata quality and category specificity, and public-set results should not be interpreted as proof of performance on arbitrary real-user language or private evaluation data.

## Limitations and future work

- **Offline catalog constraints.** The system can recommend only products present in the frozen catalog and cannot reflect inventory, shipping, changing prices, or newly released products.
- **Metadata quality.** Retrieval is bounded by the quality and completeness of titles, descriptions, features, categories, details, prices, and stores. Sparse or overlapping metadata can leave several products observationally indistinguishable.
- **Synthetic dialogue setting.** Public sessions are simulator-driven representations of shopping intent, not real customer conversations. Behavior that helps on a released evaluator may not generalize; this is why the `other`-optimized mode is kept separate from the default.
- **Heuristic evidence extraction.** The agent recognizes a finite set of structured cues and may miss novel phrasing, nuanced preferences, negation, or requests outside the supported catalog attributes.
- **Compute and startup time.** The agent creates an in-memory SQLite index and runs self-play-derived planning logic locally. This is intentionally self-contained, but startup and rollout cost should be profiled under any final CPU/memory limits.
- **No natural-language generation model.** Question templates are clear but fixed. A future version could improve conversational tone while preserving the evaluator's structured `ask_attribute` contract.

With more time, the highest-value improvements would be: evaluate on fresh human-written dialogues; measure latency/memory on the target scoring hardware; learn better catalog-only ranking features from a properly separated training set; add robust language understanding for paraphrase and negation; and test calibrated abstention/explanations without leaking evaluator-specific behavior.

## Team contributions

Update this section with the final team roster before submission. Suggested format:

| Team member | Contributions |
| --- | --- |
| Ian | Problem framing, system architecture, and project coordination |
| Jonathan | Retrieval/indexing, constraint extraction, and ranking |
| Ian | Planning, evaluation, experiments, and reproducibility |
| Hao En | Demo video, Devpost submission, documentation, and presentation |

## Data use and security

The catalog and sessions are derived from Amazon Reviews 2023 by McAuley Lab at UCSD. Use the data only under the applicable source terms and competition/research permissions. See [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md) for the project attribution and restrictions.

Never commit secrets, credentials, private evaluation data, raw user data, or organizer-only files. This repository's `.gitignore` excludes the downloaded catalog, `results.json`, `.env` files, and private/organizer paths. The submitted runtime does not require API keys.

## License and acknowledgements

This project uses the organizer-provided challenge materials and product metadata derived from Amazon Reviews 2023. The competition organizer does not claim ownership of the underlying Amazon review or product content. Please retain the attribution in [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md) when using or redistributing permitted portions of the project.
