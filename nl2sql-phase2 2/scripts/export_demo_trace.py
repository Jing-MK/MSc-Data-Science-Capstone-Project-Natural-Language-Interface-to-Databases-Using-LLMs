"""Run the real system on the demo cases and export a replayable trace
(candidates, result tables, triage decisions, questions) as JSON.

The questions and SQL are the REAL ones from the BIRD dev set
(question_ids 86, 63; searchable in dev.json). The execution is real.

For the ASK case (QID 63), rule-based enumeration alone cannot construct
the gold projection, so the correct option only appears once the
`llm_propose` hook is enabled. Because this offline export cannot call the
live API, the LLM-proposed candidate is PRE-RECORDED (clearly flagged in
the trace as source "llm", pre_recorded=True). On a machine with a real
DASHSCOPE_API_KEY, the same candidate is produced live.

Usage:
    python scripts/make_demo_db.py data/dev_databases
    python scripts/export_demo_trace.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nl2sql.config import Config, BirdConfig, FrameworkConfig
from nl2sql.agents.base import AgentContext
from nl2sql.engine.execution import Executor, result_key
from nl2sql.engine.orchestrator import Orchestrator
from nl2sql.engine.schema import SchemaReader
from nl2sql.system import default_agents
from nl2sql.types import Candidate


DEMO_CASES = [
    {
        "id": "autofix", "qid": "86", "db_id": "california_schools",
        "title": "Objective signal → AUTO-FIX (no user needed)",
        "subtitle": "Rule-based agents alone fix this: the predicate agent "
                    "finds the real stored value, and the empty-vs-non-empty "
                    "signal decides.",
        "question": "What is the administrator's last name that oversees the "
                    "school with Charter number 40? Indicate the district, the "
                    "county where the school is situated, and the name of the school.",
        "evidence": "",
        "pred_sql": "SELECT AdmLName1, District, County, School FROM schools "
                    "WHERE CharterNum = '40'",
        "gold_sql": "SELECT AdmLName1, District, County, School FROM schools "
                    "WHERE CharterNum = '0040'",
        "expected": "AUTO_FIX",
        "llm_candidate": None,
    },
    {
        "id": "ask", "qid": "63", "db_id": "california_schools",
        "title": "Intent-dependent divergence → ASK the user",
        "subtitle": "The correct column set is only proposed once the LLM hook "
                    "is enabled; the user then picks the intended answer table.",
        "question": "In chartered schools with charter number 00D2, what are the "
                    "names of all the administrators? Indicate their full names, "
                    "the name of the school and the city.",
        "evidence": "",
        "pred_sql": "SELECT School, City, AdmFName1, AdmLName1, AdmFName2, "
                    "AdmLName2, AdmFName3, AdmLName3 FROM schools "
                    "WHERE Charter = 1 AND CharterNum = '00D2'",
        "gold_sql": "SELECT AdmFName1, AdmLName1, School, City FROM schools "
                    "WHERE Charter = 1 AND CharterNum = '00D2'",
        "expected": "ASK",
        # Pre-recorded llm_propose output (the correct 4-column projection).
        "llm_candidate": {
            "axis": "projection",
            "sql": "SELECT AdmFName1, AdmLName1, School, City FROM schools "
                   "WHERE Charter = 1 AND CharterNum = '00D2'",
            "note": "LLM-proposed column set: the four fields the question asks "
                    "for (full name, school, city)",
        },
    },
    {
        "id": "abstain", "qid": None, "db_id": "california_schools",
        "title": "No real alternative → ABSTAIN (never corrupt a correct query)",
        "subtitle": "When every candidate agrees on the result, the framework "
                    "changes nothing — its safeguard against breaking a correct query.",
        "question": "List the names of schools in Fresno county.",
        "evidence": "",
        "pred_sql": "SELECT School FROM schools WHERE County = 'Fresno'",
        "gold_sql": "SELECT School FROM schools WHERE County = 'Fresno'",
        "expected": "ABSTAIN",
        "llm_candidate": None,
    },
]


def table(res):
    return {"ok": res.ok, "columns": res.columns,
            "rows": [[("" if c is None else str(c)) for c in row] for row in res.rows[:8]],
            "row_count": res.row_count, "error": res.error}


def build_trace(cfg: Config, case: dict) -> dict:
    db_id = case["db_id"]
    ex = Executor(cfg.db_path(db_id))
    reader = SchemaReader(cfg.db_path(db_id))
    schema = reader.read(db_id)
    orch = Orchestrator(ex)

    gold_key = result_key(ex.run(case["gold_sql"]))

    ctx = AgentContext(question=case["question"], evidence=case["evidence"],
                       predicted_sql=case["pred_sql"], schema=schema,
                       reader=reader, llm=None, use_llm=False)
    cands = [Candidate(sql=case["pred_sql"], axis="baseline",
                       source="baseline", note="the baseline prediction")]
    for agent in default_agents():
        try:
            cands.extend(agent.enumerate(ctx))
        except Exception:
            continue

    # Pre-recorded LLM candidate (flagged), if this case needs it.
    llm = case.get("llm_candidate")
    if llm:
        cands.append(Candidate(sql=llm["sql"], axis=llm["axis"], source="llm",
                               note=llm["note"]))

    cand_views = []
    for c in cands:
        r = ex.run(c.sql)
        cand_views.append({
            "axis": c.axis, "source": c.source, "note": c.note,
            "sql": c.sql, "objective": c.objective,
            "pre_recorded": (c.source == "llm"),
            "table": table(r), "matches_gold": result_key(r) == gold_key,
        })

    outcome = orch.triage(cands)
    triage = {"action": outcome.action.value, "reason": outcome.reason,
              "axis": outcome.axis}
    question = None
    if outcome.question:
        question = {
            "prompt": outcome.question.prompt,
            "options": [{
                "label": o.label, "columns": o.columns,
                "rows": [[("" if c is None else str(c)) for c in row] for row in o.rows[:8]],
                "matches_gold": result_key(ex.run(o.sql)) == gold_key,
                "from_llm": any(cc.sql == o.sql and cc.source == "llm" for cc in cands),
            } for o in outcome.question.options],
        }

    return {
        "id": case["id"], "qid": case["qid"], "title": case["title"],
        "subtitle": case["subtitle"], "db_id": db_id,
        "question": case["question"], "evidence": case["evidence"],
        "pred_sql": case["pred_sql"], "gold_sql": case["gold_sql"],
        "expected": case["expected"], "uses_llm": bool(llm),
        "pred_table": table(ex.run(case["pred_sql"])),
        "gold_table": table(ex.run(case["gold_sql"])),
        "candidates": cand_views, "triage": triage, "ask_question": question,
    }


def main() -> int:
    cfg = Config()
    cfg.bird = BirdConfig(db_root="data/dev_databases")
    cfg.framework = FrameworkConfig(max_rounds=4, use_llm_propose=False)

    traces = [build_trace(cfg, c) for c in DEMO_CASES]
    Path("ui").mkdir(exist_ok=True)
    with open("ui/demo_trace.json", "w", encoding="utf-8") as f:
        json.dump(traces, f, ensure_ascii=False, indent=2)
    with open("demo_cases/demo_trace.json", "w", encoding="utf-8") as f:
        json.dump(traces, f, ensure_ascii=False, indent=2)
    print("Wrote ui/demo_trace.json with", len(traces), "cases")
    for t in traces:
        qid = f"QID {t['qid']}" if t['qid'] else "(correct query)"
        print(f"  {t['id']:8} {qid:16} expected={t['expected']:9} "
              f"got={t['triage']['action']} uses_llm={t['uses_llm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
