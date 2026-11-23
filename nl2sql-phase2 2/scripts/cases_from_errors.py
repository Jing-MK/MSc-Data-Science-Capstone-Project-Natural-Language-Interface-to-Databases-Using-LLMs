"""Build cases.json directly from a baseline eval_results.json that already
contains the 477 error cases (fields: qid, question, evidence, db_id,
gold_sql, pred_sql). Use this INSTEAD of build_cases.py when you already
have the error set and only want to evaluate those cases.

Usage:
    python scripts/cases_from_errors.py \
        --errors /path/to/eval_results.json \
        --out    data/cases_477.json
"""
from __future__ import annotations

import argparse
import json


def strip_suffix(sql: str) -> str:
    return sql.split("----- bird -----")[0].strip().rstrip(";")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.errors, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Accept either a bare list or {"error_cases": [...]}.
    rows = data["error_cases"] if isinstance(data, dict) else data

    cases = []
    for r in rows:
        cases.append({
            "qid": str(r.get("qid", "")),
            "db_id": r["db_id"],
            "question": r.get("question", ""),
            "evidence": r.get("evidence", "") or "",
            "difficulty": r.get("difficulty", ""),
            "gold_sql": strip_suffix(r["gold_sql"]),
            "pred_sql": strip_suffix(r["pred_sql"]),
        })

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(cases)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
