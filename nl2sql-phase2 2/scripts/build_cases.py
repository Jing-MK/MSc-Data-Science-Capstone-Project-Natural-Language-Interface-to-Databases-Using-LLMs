"""Merge BIRD dev.json (gold) with a prediction file into cases.json.

The prediction file is the DIN-SQL / DeepEye-SQL output: a JSON object
mapping question_id (string) to a predicted SQL string that may carry a
trailing '\\t----- bird -----\\t<db_id>' marker.

Usage:
    python scripts/build_cases.py \
        --dev path/to/dev.json \
        --pred path/to/predict_dev_qwen_plus.json \
        --out data/cases.json
"""
from __future__ import annotations

import argparse
import json


def strip_suffix(sql: str) -> str:
    return sql.split("----- bird -----")[0].strip().rstrip(";")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.dev, "r", encoding="utf-8") as f:
        dev = json.load(f)
    with open(args.pred, "r", encoding="utf-8") as f:
        pred = json.load(f)

    cases = []
    for item in dev:
        qid = str(item["question_id"])
        if qid not in pred:
            continue
        cases.append({
            "qid": qid,
            "db_id": item["db_id"],
            "question": item["question"],
            "evidence": item.get("evidence", ""),
            "difficulty": item.get("difficulty", ""),
            "gold_sql": strip_suffix(item["SQL"]),
            "pred_sql": strip_suffix(pred[qid]),
        })

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(cases)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
