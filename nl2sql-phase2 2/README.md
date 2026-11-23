<div align="center">

# Natural-Language → SQL
### A Multi-Agent, Human-in-the-Loop Framework for Correcting NL2SQL Errors at Run Time

Deciding, for each residual error of a strong NL2SQL baseline — **with no gold
query available** — whether to **repair it automatically**, **ask the user**,
or **leave it untouched**.

![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![benchmark](https://img.shields.io/badge/benchmark-BIRD%20dev-orange)
![status](https://img.shields.io/badge/status-research-informational)

*MSc Data Science Capstone · MSDS/25/S2/55 · College of Computing and Data Science,
Nanyang Technological University*

</div>

---

## Table of contents

- [Overview](#overview)
- [Interactive demo](#interactive-demo)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Installation](#installation)
- [Quick start (no BIRD download)](#quick-start-no-bird-download)
- [Reproducing the evaluation](#reproducing-the-evaluation)
- [Results](#results)
- [Design notes and limitations](#design-notes-and-limitations)
- [Citation](#citation)
- [License](#license)

---

## Overview

A deployed NL2SQL system has no gold query, so when it returns an answer it
cannot know whether that answer is correct. On a strong baseline the residual
errors are:

- **silent** — 65.6% return the same number of rows as the gold query, so they
  cannot be found by anomaly detection;
- **shallow but multi-dimensional** — fixable by editing one clause in only
  21.9% of cases, but four clauses cover 92.1%;
- **bidirectional** — e.g. adding a `DISTINCT` fixes 46 queries but breaks 58,
  because whether to deduplicate depends on user *intent*, not on any
  observable signal.

So a fixed repair rule cannot win. This framework instead **triages**. A set of
agents, one per SQL *decision point*, enumerate alternative candidate queries;
the candidates are executed and **clustered by result**; and the cluster
structure decides whether an objective signal can repair the query, whether the
user must choose (shown **competing result tables, not SQL**), or whether
nothing really differs and the query should be left alone. **The decision to
involve the user rests on observed execution behaviour, never on a model judging
its own output.**

**Contributions.**
1. A gold-free, execution-signal-driven **triage** that decides *whether* to fix,
   ask, or abstain — targeting the silent-error regime that dominates a strong
   baseline.
2. A **human-in-the-loop** interaction in which a non-expert chooses between
   **result tables**, never SQL.
3. A design that **combines** decision-point structural agents with error-type
   semantic agents, with the LLM confined to proposing candidates and phrasing
   questions.
4. A reproducible **four-arm evaluation** isolating the triage policy from the
   candidate generator.

---

## Interactive demo

Open **`ui/demo_standalone.html`** in a browser — no server needed. It replays
three **real BIRD dev cases** (searchable by `question_id`), one per triage
branch, step by step:

| Case | BIRD QID | Error | Triage |
|---|---|---|---|
| Zero-padded charter number | **86** | `CharterNum = '40'` vs `'0040'` (pred returns 0 rows) | **AUTO-FIX** — objective signal (empty vs non-empty), no user needed |
| Extra projected columns | **63** | pred projects 8 columns, gold 4 | **ASK** — the user picks the intended answer table |
| Prediction already correct | — | no real alternative | **ABSTAIN** — never corrupt a correct query |

The queries are the **real** dev-set SQL and the result tables are **genuinely
executed** — not mocked — on a small stand-in database that mirrors the real
`california_schools` schema, so the demo runs without the full BIRD download.

> **Honest note on the ASK case.** For QID 63, rule-based enumeration alone
> cannot construct the gold projection, so the correct option only appears once
> the `llm_propose` hook is enabled. This offline demo makes no live API call,
> so the LLM-proposed candidate there is **pre-recorded** (flagged in the UI as
> "LLM · pre-rec"). On a machine with a real `DASHSCOPE_API_KEY`, the same
> candidate is produced live — see the live-mode server in
> [`RUN_EVAL.md`](RUN_EVAL.md).

---

## How it works

```
             ┌─────────────────────────────────────────────────────────┐
  question   │  Decision-point agents          Execution + clustering  │
  evidence   │  ┌───────────┐                   ┌───────────────────┐   │
  predicted ─┼─▶│ projection│ enumerate ──┐     │ run every candidate│   │
  SQL        │  │ predicate │ candidates  ├────▶│ cluster by result  │   │
  db schema  │  │ join, …   │             │     │ (order-insensitive)│   │
             │  │ evidence  │ ◀ LLM hook  ┘     └─────────┬─────────┘   │
             │  └───────────┘                             │             │
             │                         ┌──────────────────▼──────────┐  │
             │                         │          TRIAGE             │  │
             │     one cluster ───────▶│  ABSTAIN  (leave untouched) │  │
             │     objective signal ──▶│  AUTO-FIX (repair)          │  │
             │     intent-dependent ──▶│  ASK  (user picks a table)  │  │
             │                         └──────────────────┬──────────┘  │
             │   constraints ◀── user's answer ───────────┘             │
             │   re-probe until clusters collapse (≤ 4 rounds)          │
             └─────────────────────────────────────────────────────────┘
```

**Agents are organised by SQL decision point, not by error type.** Each agent
owns one clause (projection `D2`, predicate `D6`, join `D1`, distinct `D3`,
aggregate `D4`, group-by `D5`, order `D7`, arithmetic `D8`) and exposes a single
capability — `enumerate` — proposing candidate queries that differ from the
prediction only along that clause. No agent diagnoses *why* a query is wrong
(that needs the gold query); it only proposes what else the clause could
plausibly be. Two **semantic agents** (`evidence`, `question-entity`) add
error-type reasoning on top of the clause-grounded ones.

**The LLM is confined to two tasks** (everything else is deterministic and
inspectable): proposing candidates for the open-ended projection/predicate
clauses (the `llm_propose` hook), and phrasing a clarification question in
natural language. The decision of *whether* to involve the user never rests on
the model.

---

## Repository layout

```
nl2sql/
  config.py             configuration (API key read from env / local file)
  types.py              Candidate, Cluster, Question, TriageOutcome, …
  engine/
    execution.py        SQLite execution + order-insensitive result keys
    schema.py           schema / foreign-key / column-domain reader
    orchestrator.py     clustering + the three-way triage policy
  agents/
    projection.py  predicate.py  join.py  arithmetic.py  simple_clauses.py
    semantic.py         evidence & question-entity agents
  hitl/interaction.py   multi-round loop (shows result tables, not SQL)
  llm/client.py         Qwen (DashScope) client — the two LLM touch-points
  evaluation/
    run_eval.py         four-arm evaluation (report Chapter 6)
    arms.py  metrics.py
  system.py             CorrectionSystem — wires it all together
ui/
  index.html            interactive demo (+ demo_standalone.html, single file)
  server.py             optional live-mode server (real DB + real API)
scripts/
  cases_from_errors.py  build cases from an existing error set (477 / 417)
  build_cases.py        build cases from dev.json + predictions
  make_demo_db.py       build the self-contained demo database
  export_demo_trace.py  produce the demo traces
  smoke_test.py         end-to-end test of the three triage branches
RUN_EVAL.md             step-by-step evaluation reproduction guide
config.example.yaml     copy to config.local.yaml (git-ignored) and fill in
```

---

## Installation

```bash
pip install -r requirements.txt           # or: pip install -e ".[all]"
cp config.example.yaml config.local.yaml  # then edit config.local.yaml
```

`config.local.yaml` is **git-ignored** and holds your settings:

```yaml
llm:
  api_key: "sk-..."          # or set DASHSCOPE_API_KEY (takes precedence)
  model: "qwen-plus"
bird:
  db_root: "/path/to/bird/dev_databases"   # one <db_id>/<db_id>.sqlite per DB
framework:
  use_llm_propose: true
```

> **🔒 API keys never live in this repository.** The key is read from the
> environment variable `DASHSCOPE_API_KEY` or from `config.local.yaml`, which
> `.gitignore` excludes. Do not commit a key; if one was ever committed, rotate
> it.

---

## Quick start (no BIRD download)

```bash
python scripts/make_demo_db.py data/dev_databases
python scripts/smoke_test.py
# [PASS] AUTO_FIX — QID 86   [PASS] ABSTAIN   [PASS] ASK — QID 63   → ALL PASS
```

---

## Reproducing the evaluation

Full instructions, including both baselines and cost/time guidance, are in
**[`RUN_EVAL.md`](RUN_EVAL.md)**. In brief:

```bash
# 1. Build the case file from an existing error set (recommended)
python scripts/cases_from_errors.py \
    --errors /path/to/dinsql_eval_results.json --out data/cases_dinsql.json

# 2. Lower bound (LLM off, matches the report's setting)
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_dinsql.json --no-llm --out data/eval_dinsql_llm_off.json

# 3. Full system (LLM on)
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_dinsql.json --out data/eval_dinsql_llm_on.json
```

The four arms share the same candidate pool, so the comparison isolates the
**triage policy**:

| Arm | Policy |
|---|---|
| `no_correction` | baseline prediction, unchanged (lower bound) |
| `fix_always` | auto-select on any divergence, never ask |
| `ask_always` | consult the user on every divergence |
| `triage` (ours) | auto-fix on an objective signal, ask otherwise, abstain when nothing differs |

The user is simulated by an **oracle** that selects the candidate whose result
matches the gold query, isolating the quality of the triage from whether a real
user answers correctly. Metrics: `N_fix`, `N_break`, `N_net`, and questions per
query.

---

## Results

Run on the BIRD development set. The LLM-off columns are the reproducible lower
bound reported in the thesis; the LLM-on columns enable the `llm_propose` hook.
*(Populate from your own runs — see [`RUN_EVAL.md`](RUN_EVAL.md).)*

**DIN-SQL + Qwen-Plus — 477 errors (EX 68.9%)**



**DeepEye-SQL — 417 errors (EX 72.82%)** 

**Headline.** Across baselines, triage breaks **zero** correct queries and asks
**fewer** questions than always asking, while recovering the same errors;
recovery is bounded by candidate enumeration, which the LLM-on runs raise.

---

## Design notes and limitations

- **Enumeration is the ceiling.** Rule-based enumeration reaches the *structural*
  and *lexical* variants of a clause, but not the *semantic* alternatives that
  dominate a hard benchmark (choosing between two plausible columns). The
  `llm_propose` hook is the intended remedy; quantifying its gain is the main
  direction for future work.
- **The oracle user is idealised.** It always selects the correct option when
  present, so the results measure the quality of the triage under a perfect
  respondent, not end-to-end accuracy with human subjects. A user study is future
  work.
- **Benchmark gold queries are imperfect.** A subset of apparent "errors" are
  annotation choices rather than model failures; the framework treats errors that
  differ from the gold at no decision point as candidates for gold revision rather
  than repair.

---

## Citation

If you use this software or build on it, please cite it (see
[`CITATION.cff`](CITATION.cff)):

```bibtex
@software{wang2026nl2sql_triage,
  author  = {Wang, Yijing},
  title   = {A Multi-Agent, Human-in-the-Loop Framework for Correcting
             Natural-Language-to-SQL Errors at Run Time},
  year    = {2026},
  note    = {MSc Data Science Capstone, Nanyang Technological University},
  license = {MIT}
}
```

---

## License

Released under the [MIT License](LICENSE).
