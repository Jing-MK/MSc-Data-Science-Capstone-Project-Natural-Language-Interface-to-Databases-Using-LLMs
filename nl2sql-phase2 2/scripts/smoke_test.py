"""End-to-end smoke test on the self-contained demo database.

Builds the demo DB and checks that the real BIRD demo cases exercise the
correct branch of the triage policy and reach the gold result. Run:

    python scripts/make_demo_db.py data/dev_databases
    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nl2sql.config import Config, BirdConfig, FrameworkConfig
from nl2sql.engine.execution import Executor, result_key
from nl2sql.system import CorrectionSystem
from nl2sql.types import Candidate


def main() -> int:
    cfg = Config()
    cfg.bird = BirdConfig(db_root="data/dev_databases")
    cfg.framework = FrameworkConfig(max_rounds=4, use_llm_propose=False)
    system = CorrectionSystem(cfg)
    db = "california_schools"
    ex = Executor(cfg.db_path(db))

    def oracle(gold_key):
        def user(q):
            for i, opt in enumerate(q.options):
                if result_key(ex.run(opt.sql)) == gold_key:
                    return i
            return 0
        return user

    # AUTO_FIX (QID 86) and ABSTAIN are solved by rule agents alone.
    cases = [
        ("AUTO_FIX — QID 86 (zero-padded charter number)", "AUTO_FIX",
         "SELECT AdmLName1, District, County, School FROM schools WHERE CharterNum = '40'",
         "SELECT AdmLName1, District, County, School FROM schools WHERE CharterNum = '0040'"),
        ("ABSTAIN — correct query left untouched", "ABSTAIN",
         "SELECT School FROM schools WHERE County = 'Fresno'",
         "SELECT School FROM schools WHERE County = 'Fresno'"),
    ]

    all_pass = True
    for name, expected, pred, gold in cases:
        gk = result_key(ex.run(gold))
        res = system.correct(db, "", "", pred, oracle(gk))
        ok = result_key(ex.run(res.final_sql)) == gk
        got = ("ASK" if "ask" in res.action_trace
               else "AUTO_FIX" if "auto_fix" in res.action_trace else "ABSTAIN")
        status = "PASS" if (got == expected and ok) else "FAIL"
        all_pass &= (got == expected and ok)
        print(f"[{status}] {name}")
        print(f"        actions={res.action_trace} questions={res.questions_asked} correct={ok}")

    # ASK (QID 63): the correct projection is only reachable with the LLM hook.
    # Here we inject the pre-recorded LLM candidate and check the user can
    # then pick the gold-matching answer table.
    pred63 = ("SELECT School, City, AdmFName1, AdmLName1, AdmFName2, AdmLName2, "
              "AdmFName3, AdmLName3 FROM schools WHERE Charter = 1 AND CharterNum = '00D2'")
    gold63 = ("SELECT AdmFName1, AdmLName1, School, City FROM schools "
              "WHERE Charter = 1 AND CharterNum = '00D2'")
    from nl2sql.engine.orchestrator import Orchestrator
    from nl2sql.agents.base import AgentContext
    from nl2sql.engine.schema import SchemaReader
    from nl2sql.system import default_agents
    reader = SchemaReader(cfg.db_path(db))
    schema = reader.read(db)
    orch = Orchestrator(ex)
    ctx = AgentContext(question="", evidence="", predicted_sql=pred63,
                       schema=schema, reader=reader, llm=None, use_llm=False)
    cands = [Candidate(sql=pred63, axis="baseline", source="baseline", note="base")]
    for a in default_agents():
        cands.extend(a.enumerate(ctx))
    cands.append(Candidate(sql=gold63, axis="projection", source="llm",
                           note="LLM-proposed column set"))
    out = orch.triage(cands)
    gk = result_key(ex.run(gold63))
    has_gold = out.question and any(result_key(ex.run(o.sql)) == gk
                                    for o in out.question.options)
    ok = (out.action.value == "ask" and has_gold)
    all_pass &= ok
    print(f"[{'PASS' if ok else 'FAIL'}] ASK — QID 63 (LLM-proposed option present)")
    print(f"        action={out.action.value} options={len(out.question.options) if out.question else 0} "
          f"gold_among_options={has_gold}")

    print("\nALL PASS" if all_pass else "\nSOME FAILED")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
