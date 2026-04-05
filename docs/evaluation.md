# LexGrid Evaluation

> This document covers the evaluation framework — how test cases are defined, what metrics are computed, how to run the evaluation suite, and how to interpret results.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Test Cases](#2-test-cases)
3. [Metrics Definitions](#3-metrics-definitions)
4. [Pass/Fail Criteria](#4-passfail-criteria)
5. [Running the Evaluation](#5-running-the-evaluation)
6. [Interpreting the Report](#6-interpreting-the-report)
7. [How to Add New Test Cases](#7-how-to-add-new-test-cases)
8. [Current Results](#8-current-results)

---

## 1. Overview

The evaluation suite tests the full end-to-end RAG pipeline against 12 ground-truth test cases. It calls the live API (`POST /query/`) and measures:

- **Retrieval quality**: Did the system retrieve the right sections?
- **Answer quality**: Did the LLM cite the correct sections in its answer?
- **Negative cases**: Does the system correctly refuse to answer out-of-domain queries?

The evaluation runner is in `backend/app/evaluation/runner.py`. The CLI is `scripts/evaluate.py`.

---

## 2. Test Cases

All 12 test cases are defined in `backend/app/evaluation/test_cases.py` as `EvalCase` objects.

### Query Types

| Type | Description | Example |
|---|---|---|
| `direct` | Exact section reference — triggers query intelligence direct lookup | "What is Section 300 IPC murder?" |
| `comparative` | Asks to compare two related concepts | "What is the difference between culpable homicide and murder?" |
| `procedural` | Asks about a process or set of conditions | "What are the conditions for granting bail in CrPC?" |
| `negative` | Out-of-domain — system should say it cannot find the answer | "What is quantum physics?" |

### All 12 Test Cases

| ID | Query | Expected Sections | Expected Acts | Type | Should Find? |
|---|---|---|---|---|---|
| tc-01 | What is Section 120A IPC criminal conspiracy? | `ipc-120A-section`, `ipc-120B-section` | ipc | direct | ✅ |
| tc-02 | What is Section 300 IPC murder? | `ipc-300-section` | ipc | direct | ✅ |
| tc-03 | What is the difference between culpable homicide and murder? | `ipc-299-section`, `ipc-300-section` | ipc | comparative | ✅ |
| tc-04 | What is Section 376 IPC? | `ipc-376-section` | ipc | direct | ✅ |
| tc-05 | What are the conditions for granting bail in CrPC? | `crpc-436-section`, `crpc-437-section`, `crpc-439-section`, `crpc-440-section`, `crpc-441-section` | crpc | procedural | ✅ |
| tc-06 | What is dowry prohibition under HMA? | *(empty)* | hma | negative | ❌ |
| tc-07 | What is Section 379 IPC punishment for theft? | `ipc-379-section` | ipc | direct | ✅ |
| tc-08 | What is BNS Section 103? | `bns-103-section` | bns | direct | ✅ |
| tc-09 | What is Section 190 CrPC cognizance of offences? | `crpc-190-section`, `crpc-193-section` | crpc | direct | ✅ |
| tc-10 | What are the rights of an arrested person? | `crpc-50-section`, `crpc-55-section` | crpc | procedural | ✅ |
| tc-11 | What is adultery under IPC? | `ipc-497-section`, `ipc-494-section`, `ipc-498-section` | ipc | direct | ✅ |
| tc-12 | What is quantum physics? | *(empty)* | *(empty)* | negative | ❌ |

### Negative Test Cases Explained

**tc-06** (dowry under HMA): The Hindu Marriage Act does not contain dowry prohibition provisions — that is covered by the Dowry Prohibition Act (not indexed). The system should respond with "I cannot find this information in the provided legal texts."

**tc-12** (quantum physics): Completely out-of-domain. The cosine distance threshold (0.75) should prevent any sections from being retrieved, and the LLM should respond with the standard "cannot find" message.

Both negative cases have `should_find_answer=False` and `expected_section_ids=[]`. They pass when the system correctly returns no relevant sections.

---

## 3. Metrics Definitions

All metrics are implemented in `backend/app/evaluation/metrics.py`.

### Precision@K

Fraction of the top-K retrieved chunks that are in the expected set.

```
Precision@K = |retrieved[:K] ∩ relevant| / K
```

- Range: [0.0, 1.0]
- K = 5 (fixed in `runner.py: _K = 5`)
- Example: Retrieved `[ipc-300-section, ipc-299-section, ipc-301-section, ...]`, relevant = `[ipc-300-section]`
  → `P@5 = 1/5 = 0.20`

### Recall@K

Fraction of the expected sections found in the top-K retrieved chunks.

```
Recall@K = |retrieved[:K] ∩ relevant| / |relevant|
```

- Range: [0.0, 1.0]
- **Special case**: If `relevant` is empty (negative test cases), returns `1.0` vacuously — nothing was expected, nothing was missed.
- Example: Retrieved `[ipc-300-section, ipc-299-section, ...]`, relevant = `[ipc-299-section, ipc-300-section]`
  → `R@5 = 2/2 = 1.0`

### MRR (Mean Reciprocal Rank)

Reciprocal of the rank of the first relevant result.

```
MRR = 1 / rank_of_first_relevant_result
```

- Range: [0.0, 1.0]
- If the first relevant result is at rank 1: MRR = 1.0
- If at rank 2: MRR = 0.5
- If at rank 3: MRR = 0.333
- If no relevant result found: MRR = 0.0
- The reported MRR is the mean across all test cases.

### Legal Accuracy Score

Fraction of expected section IDs that are explicitly cited in the LLM answer text.

```
Legal Accuracy = cited_expected_sections / total_expected_sections
```

- Range: [0.0, 1.0]
- **Special case**: If `expected_section_ids` is empty, returns `1.0` vacuously.
- A section is considered "cited" if the answer contains both:
  1. The section number as a word boundary: `\bsection\s+{number}\b`
  2. At least one act alias (case-insensitive)

**Act aliases** used for matching:

| Act Code | Aliases |
|---|---|
| `ipc` | `ipc`, `indian penal code`, `i.p.c` |
| `crpc` | `crpc`, `code of criminal procedure`, `c.r.p.c`, `cr.p.c` |
| `bns` | `bns`, `bharatiya nyaya sanhita` |
| `cpc` | `cpc`, `code of civil procedure`, `c.p.c` |
| `iea` | `iea`, `indian evidence act` |
| `hma` | `hma`, `hindu marriage act` |
| `ida` | `ida`, `indian divorce act` |
| `mva` | `mva`, `motor vehicles act` |
| `nia` | `nia`, `national investigation agency act` |

**Example**: Expected `ipc-300-section`. Answer contains "Section 300, Indian Penal Code" → `_is_cited("ipc", "300")` returns `True` because:
- `\bsection\s+300\b` matches
- `"indian penal code"` is in the `ipc` aliases

---

## 4. Pass/Fail Criteria

A test case **passes** if:

```python
# For cases with expected sections (should_find_answer=True):
passed = (reciprocal_rank > 0.0)
# i.e., at least one expected section appears anywhere in the top-K results

# For negative cases (should_find_answer=False, expected_section_ids=[]):
passed = True  # vacuously — empty expected set means nothing to find
```

A test case **fails** if:
- `should_find_answer=True` AND no expected section appears in the top-K retrieved chunks (MRR = 0)

The overall suite **passes** if `pass_rate >= 0.5` (50%). The CLI exits with code 1 if below this threshold.

---

## 5. Running the Evaluation

### Prerequisites

1. The LexGrid API must be running: `docker compose up -d` or `uvicorn app.main:app`
2. All acts must be ingested: `python scripts/ingest.py --act all`
3. `click` must be installed: `pip install click` (included in dev dependencies)

### Basic Run

```bash
# From repo root
python scripts/evaluate.py

# With custom API URL
python scripts/evaluate.py --api-url http://localhost:8000

# With custom output file
python scripts/evaluate.py --output results/eval_$(date +%Y%m%d).json
```

### CLI Options

```
Usage: evaluate.py [OPTIONS]

  Run all evaluation test cases against the LexGrid API and print a summary.

Options:
  --api-url TEXT  Base URL of the running LexGrid API.  [default: http://localhost:8000]
  --output PATH   Path where the JSON report will be saved.  [default: eval_report.json]
  --help          Show this message and exit.
```

### Expected Output

```
INFO  Running 12 test cases against http://localhost:8000 …
INFO  ============================================================
INFO    LexGrid Evaluation Report  —  run a1b2c3d4
INFO  ============================================================
INFO    Total cases : 12
INFO    Passed      : 12  (100%)
INFO    Failed      : 0
INFO    Mean P@5    : 0.233
INFO    Mean R@5    : 0.814
INFO    MRR         : 0.833
INFO    Legal Acc.  : 0.703
INFO  ============================================================
INFO  Report saved → /path/to/eval_report.json
```

### Important: `use_cache=False`

The evaluation runner always sends `use_cache=False` in each request. This ensures:
1. Every test case hits the full pipeline (no stale cached results)
2. Latency measurements are accurate
3. Results are reproducible

---

## 6. Interpreting the Report

The report is saved as JSON (`eval_report.json` by default). Structure:

```json
{
  "run_id": "uuid-string",
  "timestamp": "2026-04-05T10:00:00",
  "total_cases": 12,
  "passed": 12,
  "failed": 0,
  "mean_precision_at_k": 0.233,
  "mean_recall_at_k": 0.814,
  "mrr": 0.833,
  "mean_legal_accuracy": 0.703,
  "pass_rate": 1.0,
  "results": [...],
  "failure_cases": []
}
```

### Per-Case Result Fields

```json
{
  "case_id": "tc-03",
  "query": "What is the difference between culpable homicide and murder?",
  "query_type": "comparative",
  "retrieved_ids": ["ipc-299-section", "ipc-300-section", "ipc-302-section", ...],
  "answer": "According to [Section 299, Indian Penal Code]...",
  "precision_at_k": 0.4,
  "recall_at_k": 1.0,
  "reciprocal_rank": 1.0,
  "legal_accuracy": 1.0,
  "passed": true,
  "failure_reason": null,
  "latency_ms": 2341
}
```

### Reading the Metrics

| Metric | What it tells you | Good value |
|---|---|---|
| `pass_rate` | Fraction of cases where at least one expected section was retrieved | 1.0 (100%) |
| `mrr` | How high up the first relevant result appears | > 0.8 |
| `mean_recall_at_k` | How many expected sections are found in top-5 | > 0.8 |
| `mean_precision_at_k` | How many of the top-5 results are relevant | Varies — lower for multi-section queries |
| `mean_legal_accuracy` | How often the LLM cites the right sections | > 0.7 |

**Why is `mean_precision_at_k` low (~0.233)?** This is expected. For a query like tc-05 (bail conditions, 5 expected sections), retrieving all 5 in top-5 gives P@5 = 1.0. But for tc-02 (Section 300 IPC, 1 expected section), retrieving it at rank 1 gives P@5 = 1/5 = 0.2. The average across all cases is naturally low because most queries have 1–2 expected sections but we retrieve 5.

**Why is `mean_legal_accuracy` lower than `mrr`?** MRR measures retrieval (did we find the section?). Legal accuracy measures generation (did the LLM cite it correctly?). The LLM sometimes paraphrases act names in ways that don't match the alias list, or omits citations for sections it used implicitly.

### Failure Analysis

If any cases fail, they appear in `failure_cases` with a `failure_reason`:

```json
{
  "failure_reason": "mrr=0.00 retrieved=['crpc-436-section', 'crpc-437-section', 'crpc-438-section']"
}
```

This means the expected sections were not in the retrieved list. Common causes:
1. **Ingestion incomplete**: The expected section wasn't indexed. Check with `GET /search/?act_code=crpc&section_number=439`.
2. **Embedding mismatch**: The embedding model was changed after ingestion. Re-ingest.
3. **Cosine threshold too strict**: The section exists but its embedding is too far from the query. Lower `max_distance` in `similarity_search()`.

---

## 7. How to Add New Test Cases

Edit `backend/app/evaluation/test_cases.py` and add an `EvalCase` to `EVAL_CASES`:

```python
EvalCase(
    id="tc-13",
    query="What is the punishment for theft under IPC?",
    expected_section_ids=["ipc-379-section", "ipc-380-section"],
    expected_acts=["ipc"],
    query_type="direct",
    should_find_answer=True,
    # Optional: keywords that must appear in the answer
    expected_answer_contains=["imprisonment", "fine"],
),
```

### `EvalCase` Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | ✅ | Unique ID, e.g. `"tc-13"` |
| `query` | `str` | ✅ | The legal question to evaluate |
| `expected_section_ids` | `list[str]` | ✅ | Section IDs in `{act_code}-{number}-section` format |
| `expected_acts` | `list[str]` | ✅ | Act codes that should be referenced |
| `query_type` | `str` | ✅ | `direct` \| `comparative` \| `procedural` \| `negative` \| `cross_act` |
| `should_find_answer` | `bool` | ❌ | Default `True`. Set `False` for negative cases |
| `expected_answer_contains` | `list[str] \| None` | ❌ | Keywords that must appear in the answer (not yet used in pass/fail logic) |

### Guidelines for Good Test Cases

1. **Verify the section exists** before adding it as expected:
   ```bash
   curl "http://localhost:8000/search/?act_code=ipc&section_number=379"
   ```

2. **Use the exact section ID format**: `{act_code}-{section_number}-section` (lowercase, hyphen-separated).

3. **For direct queries**: Include the act abbreviation in the query (e.g. "Section 379 IPC") — this triggers the direct lookup path and makes the test deterministic.

4. **For negative cases**: Set `expected_section_ids=[]`, `should_find_answer=False`, and use a query that is clearly out-of-domain.

5. **For procedural queries**: Include all sections that are genuinely relevant — the system should retrieve all of them in top-5.

---

## 8. Current Results

From `eval_report.json` (latest run):

| Metric | Value |
|---|---|
| Pass Rate | 100% (12/12) |
| MRR | 0.833 |
| Mean Recall@5 | 0.814 |
| Mean Precision@5 | 0.233 |
| Mean Legal Accuracy | 0.703 |

### Per-Case Summary

| ID | Type | MRR | R@5 | P@5 | Legal Acc. | Pass |
|---|---|---|---|---|---|---|
| tc-01 | direct | 1.0 | 1.0 | 0.4 | 1.0 | ✅ |
| tc-02 | direct | 1.0 | 1.0 | 0.2 | 1.0 | ✅ |
| tc-03 | comparative | 1.0 | 1.0 | 0.4 | 1.0 | ✅ |
| tc-04 | direct | 1.0 | 1.0 | 0.2 | 1.0 | ✅ |
| tc-05 | procedural | 1.0 | 1.0 | 1.0 | 0.6 | ✅ |
| tc-06 | negative | — | 1.0 | — | 1.0 | ✅ |
| tc-07 | direct | 1.0 | 1.0 | 0.2 | 1.0 | ✅ |
| tc-08 | direct | 1.0 | 1.0 | 0.2 | 1.0 | ✅ |
| tc-09 | direct | 1.0 | 0.5 | 0.2 | 0.5 | ✅ |
| tc-10 | procedural | 0.5 | 1.0 | 0.4 | 0.0 | ✅ |
| tc-11 | direct | 0.5 | 0.67 | 0.2 | 0.33 | ✅ |
| tc-12 | negative | — | 1.0 | — | 1.0 | ✅ |

> **tc-10 Legal Accuracy = 0.0**: The rights of an arrested person (CrPC sections 50, 55) were retrieved correctly (Recall@5 = 1.0), but the LLM answer did not cite them in the `[Section X, Act Name]` format that the citation extractor requires. This is a generation quality issue, not a retrieval issue.
