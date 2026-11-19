# MSc-Data-Science-Capstone-Project-Natural-Language-Interface-to-Databases-Using-LLMs
# Interactive NL2SQL with a Multi-Agent Human-in-the-Loop Framework

An error-correction framework for text-to-SQL that decides, at run time and
**without a gold query**, whether to **repair** an error automatically, **ask**
the user, or **abstain** — and when it asks, the user chooses among **answer
tables**, never SQL.

> MSc Capstone Project · Nanyang Technological University (CCDS)
> Supervisor: Prof. Wang Qichen

---

## Motivation

Large language models reach high aggregate accuracy on text-to-SQL benchmarks,
but a deployed system has no gold query: when it returns an answer, it cannot
tell right from wrong. This project studies the residual errors of a **strong**
baseline and asks a different question from most prior work — not *how to
generate better SQL*, but **when a wrong query can be fixed automatically, and
when the user must be consulted.**

A clause-level analysis of the errors of two reproduced baselines motivates the
design:

| Baseline | Execution accuracy (BIRD dev) | Errors |
|---|---|---|
| DIN-SQL + Qwen-Plus | 68.9% | 477 |
| DeepEye-SQL | 72.82% | 417 |

Three findings (consistent across both baselines):

1. **Errors are silent** — 65.6% / 67.1% of wrong queries execute cleanly and
   return the same number of rows as the gold, so anomaly detection is not enough.
2. **Shallow but multi-dimensional** — one-clause repair recovers only ~22%, but
   four clause-level corrections cover ~92%.
3. **Several clauses are bidirectional** — for `DISTINCT`, aggregation and
   `GROUP BY`, any fixed rule fixes some queries and breaks as many (e.g. a net
   of −12 for an "always add `DISTINCT`" rule), because the choice depends on
   **user intent**, not on any observable signal.

---

## Approach

The framework treats correction as a **triage** problem, organised around the
eight SQL **decision points** (not error types — an error type cannot be
identified at run time without the gold query, whereas every query has a SELECT,
a WHERE, and so on).

```
                 predicted SQL
                      │
     ┌────────────────▼─────────────────┐
     │  decision-point agents ENUMERATE  │   one agent per SQL clause;
     │  candidate queries                │   each only enumerates, never
     └────────────────┬─────────────────┘   diagnoses "why wrong"
                      │
     ┌────────────────▼─────────────────┐
     │  execute all · cluster by RESULT  │   order-insensitive multiset
     └────────────────┬─────────────────┘
                      │
     ┌────────────────▼─────────────────┐
     │  TRIAGE                           │
     │   1 cluster            → ABSTAIN  │   (never alter a query with
     │   signal picks one     → REPAIR   │    no real divergence)
     │   intent-dependent     → ASK      │   (user picks an answer table)
     └───────────────────────────────────┘
```

- **Divergence is measured in execution-result space**, not SQL-text space — so
  the system never asks the user about two queries that produce the same answer.
- **The decision to involve the user rests on execution behaviour**, never on a
  model judging its own output.
- Interaction stops deterministically when the result clusters collapse to one,
  or after a 4-round budget.

---

## Repository structure

```
engine/
  execution.py       execute queries; order-insensitive result equality (BIRD EX)
  schema.py          schema / foreign-key / column-domain introspection
  context.py         per-query context passed to agents
  types.py           Candidate, Cluster, Decision, Constraint
  orchestrator.py    probe(): execute, cluster, and TRIAGE   ← core of the method
agents/              one agent per SQL decision point; each only enumerate()
  projection.py              D2 — lexical column substitution
  projection_schema_aware.py D2 — schema-aware (rewrites table alias + column)
  predicate.py               D6 — value-domain / add-drop condition
  join.py                    D1 — foreign-key graph paths
  simple_clauses.py          D3 distinct · D4 aggregate · D7 order
  arithmetic.py              D8 — CAST (integer-division), NULL, evidence formula
  ...

hitl/
  interaction.py     multi-round loop: constraints, resolved-axis tracking, stop
system.py            CorrectionSystem — assembles the agents + HITL loop
evaluation/
  build_cases.py     build cases.json from BIRD dev.json + a predictions file
  run_eval.py        three-arm evaluation (no-correction / fix-always / ask-always / triage)
  arms.py            the three correction strategies
  metrics.py         N_fix / N_break / N_net + questions-per-query
  diagnose.py        why the triage behaves as it does (enumeration vs policy)
make_db.py           builds a small demo database from real BIRD case structures
run_demo.py          end-to-end demo with an oracle user
demo_interactive.py  interactive demo — shows answer tables, user types a choice
```

---

## Quick start

Requires only Python 3 (standard library; `sqlite3` is built in).

```bash
# 1. build the small demo database
python3 make_db.py

# 2. interactive demo — the user chooses an answer table, no SQL shown
python3 demo_interactive.py

# 3. automatic end-to-end demo (oracle user, no input needed)
python3 run_demo.py
```

---

## Running the evaluation on BIRD

You need the BIRD development set and databases locally:
`dev.json`, your predictions file, and `dev_databases/` (BIRD layout
`<db_id>/<db_id>.sqlite`).

```bash
# 1. merge predictions + dev.json into cases.json
python3 -m evaluation.build_cases \
    --dev   /path/to/dev.json \
    --pred  /path/to/predict_dev_qwen_plus.json \
    --out   cases.json

# 2. evaluate only the baseline's errors (fast): how many does Phase 2 fix?
python3 -m evaluation.run_eval \
    --cases cases.json \
    --dbroot /path/to/dev_databases \
    --errors-only

# 3. diagnose the bottleneck (enumeration coverage vs triage policy)
python3 -m evaluation.diagnose --cases cases.json --dbroot /path/to/dev_databases
```

The user is simulated by an oracle that picks the option whose execution result
matches the gold query (the evaluation device used by Sphinteract).

---

## Results (first 100 errored queries, oracle user)

| Arm | N_fix | N_break | Questions / query |
|---|---|---|---|
| No correction | 0 | 0 | 0.00 |
| Fix-always (SQLENS-style) | 2 | 0 | 0.00 |
| Ask-always (Sphinteract-style) | 9 | 0 | 1.47 |
| **Triage (ours)** | **9** | **0** | **1.14** |

**What the numbers say.** The triage recovers the same errors as ask-always
while asking **22% fewer questions**, and breaks **no** correct query
(`N_break = 0`). The absolute repair rate of the rule-based system is modest
(9%): this is consistent with the error analysis — most errors are silent and
intent-dependent — and a manual inspection confirms that the unrecovered cases
need a choice among semantically plausible columns or aggregation strategies that
rule-based enumeration cannot propose.

**The contribution is the triage policy (safe, effort-reducing), not the repair
rate.** The ceiling is candidate *enumeration*, which the `llm_propose` hook is
designed to raise.

---

## Using a language model (optional)

The projection and predicate clauses face an open-ended space of alternatives.
Pass an `llm_propose` callback to supply additional candidates:

```python
from system import CorrectionSystem

def llm_propose(sql, axis):
    # return a list of (candidate_sql, human_note) for this clause
    ...

sys = CorrectionSystem("db.sqlite", llm_propose=llm_propose)
```

The language model only **proposes** candidates and **phrases** questions; every
decision (repair / ask / abstain, which question, when to stop) stays
deterministic and execution-grounded.

---

## Limitations

- **Rule-based enumeration** reaches structural, not semantic, alternatives,
  which bounds the repair rate on a hard benchmark.
- **The oracle user** is idealised; end-to-end accuracy with human subjects is
  future work.
- **The clause-level analysis** uses a regex-based SQL parser; the clause-level
  percentages are approximate (execution-derived figures such as row counts and
  empty results are exact).

---

## Related work

This framework sits between error-correction systems that auto-fix everything
and never ask (SQLENS), and interactive systems that ask on every divergence
(Sphinteract; the expected-information-gain approach of Qiu et al.). It is, to
our knowledge, the first to use an objective, gold-free signal to decide
*whether to involve the user at all*, and to measure divergence in
execution-result space rather than SQL-text space.

---

## Acknowledgements

Developed as an MSc capstone project at NTU CCDS, under the supervision of
Prof. Wang Qichen. Built on the BIRD benchmark and the DIN-SQL and DeepEye-SQL
baselines.
