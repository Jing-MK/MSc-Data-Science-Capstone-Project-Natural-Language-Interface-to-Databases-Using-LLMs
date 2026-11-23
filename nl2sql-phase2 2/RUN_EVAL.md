# Reproducing the evaluation

This guide runs the full four-arm evaluation (Chapter 6 of the report) on
your own machine, where a Qwen API key are
available. Follow it top to bottom.

> **We need:** the project, the BIRD dev databases, baseline error set(s), and (for the LLM-enabled runs) a DashScope/Qwen API key.

---

## 0. One-time setup

```bash
cd nl2sql-phase2
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
cp config.example.yaml config.local.yaml
```

Edit **`config.local.yaml`** (it is git-ignored):

```yaml
llm:
  api_key: "sk-..."                       # your Qwen/DashScope key
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen3.7-plus"
  enable_thinking: false
bird:
  db_root: "/absolute/path/to/dev_databases"   # folder with <db_id>/<db_id>.sqlite
framework:
  use_llm_propose: true
  max_rounds: 4
```

Your `db_root` should contain the 11 BIRD dev databases in the standard
layout, e.g. `dev_databases/california_schools/california_schools.sqlite`.

Alternatively, set the key in the environment (this overrides the file):

```bash
export DASHSCOPE_API_KEY="sk-..."
```

---

## 1. Build the case file

We already have the baseline
error set (the `eval_results.json` with 477 / 417 error cases).

### From an existing error set — recommended

```bash
# DIN-SQL + Qwen-Plus (477 errors)
python scripts/cases_from_errors.py \
    --errors /path/to/dinsql_eval_results.json \
    --out    data/cases_dinsql.json

# DeepEye-SQL (417 errors)
python scripts/cases_from_errors.py \
    --errors /path/to/deepeye_eval_results.json \
    --out    data/cases_deepeye.json
```


---

## 2. Smoke-test first (10 cases, no API)

Always confirm the pipeline runs before a long, paid run:

```bash
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_dinsql.json --limit 10 --no-llm
```

You should see the four-arm table print without errors.

---

## 3. Run the evaluation

Each run prints a table and writes a JSON summary. **LLM-enabled runs call
the API once or more per case, so they take time and consume quota** — start
with `--limit` to gauge speed and cost.

### DIN-SQL + Qwen-Plus (477 errors)

```bash
# Reproducible lower bound (LLM off) — matches the report's setting
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_dinsql.json --no-llm \
    --out   data/eval_dinsql_llm_off.json

# Full system (LLM on)
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_dinsql.json \
    --out   data/eval_dinsql_llm_on.json
```

### DeepEye-SQL (417 errors) — optional, shows generality

```bash
python -m nl2sql.evaluation.run_eval \
    --cases data/cases_deepeye.json --no-llm \
    --out   data/eval_deepeye_llm_off.json

python -m nl2sql.evaluation.run_eval \
    --cases data/cases_deepeye.json \
    --out   data/eval_deepeye_llm_on.json
```

---

## 4. Read the output

The printed table has one row per arm:

```
Arm              N_fix  N_break  N_net  Questions  Q/query
no_correction        0        0      0          0     0.00
fix_always          ..       ..     ..          0     0.00
ask_always          ..        0     ..        ...     ....
triage              ..        0     ..        ...     ....
```

- **N_fix** — errors made correct by the arm.
- **N_break** — previously-correct queries the arm broke (the triage arm
  should be **0**).
- **N_net** — N_fix − N_break.
- **Q/query** — questions asked per evaluated case (triage should be lower
  than ask-always).

The headline claim is that **triage breaks zero correct queries** and asks
**fewer questions** than always asking, recovering the same errors; the
repair count is bounded by candidate enumeration, which the LLM-on run
raises.

---

## 5. Cost and time tips

- Start every paid run with `--limit 20` to estimate time per case.
- `--no-llm` is free and fast; run it first for the lower-bound numbers.
- If a run is interrupted, re-run it — results are recomputed from scratch
  (there is no partial-state caching).
- The LLM is only called for the open-ended projection/predicate clauses and
  to phrase questions, so most cases incur only a few calls.

---

## 6. Live demo server (optional)

To show the system running live (real DB + real API) rather than the
pre-recorded walkthrough:

```bash
pip install flask flask-cors
python ui/server.py          # http://127.0.0.1:5000
```

The page `ui/index.html` uses the pre-recorded traces by default; the
`/api/correct` endpoint runs the real pipeline on demand.
