"""Run the four-arm evaluation (report Chapter 6) on a BIRD error set.

The user is simulated by an *oracle* that, shown the candidate answer
tables, selects the one whose execution result matches the gold query
(the same evaluation device as Zhao et al., 2024). This isolates the
triage decisions from whether a real user answers correctly.

Usage:
    python -m nl2sql.evaluation.run_eval \
        --cases data/cases.json [--limit 100] [--errors-only] \
        [--no-llm]

``cases.json`` is a list of objects with:
    db_id, question, evidence, gold_sql, pred_sql
(build it with scripts/build_cases.py).
"""
from __future__ import annotations

import argparse
import json
from typing import List

from ..config import load_config
from ..engine.execution import Executor, result_key
from ..evaluation.arms import Arm
from ..evaluation.metrics import EvalResult
from ..system import CorrectionSystem


def _oracle(executor: Executor, gold_key: str):
    def user(q):
        for i, opt in enumerate(q.options):
            if result_key(executor.run(opt.sql)) == gold_key:
                return i
        return 0
    return user


def evaluate(cases: List[dict], errors_only: bool = False,
             use_llm: bool = True, config_path: str = None) -> List[EvalResult]:
    cfg = load_config(config_path)
    cfg.framework.use_llm_propose = use_llm
    system = CorrectionSystem(cfg)

    arms = [Arm.NO_CORRECTION, Arm.FIX_ALWAYS, Arm.ASK_ALWAYS, Arm.TRIAGE]
    results = {a: EvalResult(arm=a.value) for a in arms}

    for case in cases:
        db_id = case["db_id"]
        executor = Executor(cfg.db_path(db_id), cfg.framework.busy_timeout_ms)
        gold_key = result_key(executor.run(case["gold_sql"]))
        pred_key = result_key(executor.run(case["pred_sql"]))
        baseline_correct = (pred_key == gold_key)

        if errors_only and baseline_correct:
            continue

        for arm in arms:
            r = results[arm]
            r.n_cases += 1
            if arm == Arm.NO_CORRECTION:
                final_correct = baseline_correct
                questions = 0
            else:
                mode = {
                    Arm.FIX_ALWAYS: "fix_always",
                    Arm.ASK_ALWAYS: "ask_always",
                    Arm.TRIAGE: "triage",
                }[arm]
                out = system.correct(
                    db_id, case["question"], case.get("evidence", ""),
                    case["pred_sql"], _oracle(executor, gold_key), mode=mode)
                final_correct = result_key(executor.run(out.final_sql)) == gold_key
                questions = out.questions_asked
            r.questions += questions
            if not baseline_correct and final_correct:
                r.n_fix += 1
            if baseline_correct and not final_correct:
                r.n_break += 1

    return list(results.values())


def print_table(results: List[EvalResult]) -> None:
    print(f"{'Arm':<16}{'N_fix':>7}{'N_break':>9}{'N_net':>7}"
          f"{'Questions':>11}{'Q/query':>9}")
    print("-" * 59)
    for r in results:
        print(f"{r.arm:<16}{r.n_fix:>7}{r.n_break:>9}{r.n_net:>7}"
              f"{r.questions:>11}{r.questions_per_query:>9.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True, help="path to cases.json")
    ap.add_argument("--limit", type=int, default=0, help="limit number of cases")
    ap.add_argument("--errors-only", action="store_true",
                    help="evaluate only cases the baseline gets wrong")
    ap.add_argument("--no-llm", action="store_true",
                    help="disable the llm_propose hook (rule-based lower bound)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=None, help="optional path to write JSON results")
    args = ap.parse_args()

    with open(args.cases, "r", encoding="utf-8") as f:
        cases = json.load(f)
    if args.limit:
        cases = cases[:args.limit]

    results = evaluate(cases, errors_only=args.errors_only,
                       use_llm=not args.no_llm, config_path=args.config)
    print_table(results)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump([r.row() for r in results], f, indent=2)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
