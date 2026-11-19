"""
BIRD Benchmark Evaluation Script
100% aligned with official evaluation.py (set-based comparison)
+ --limit flag for quick testing

Usage:
    # Quick test on first 20 questions
    python eval.py --pred_path predict_dev.json \
                   --dev_path dev/dev.json \
                   --db_path dev/dev_databases \
                   --limit 20

    # Full evaluation
    python eval.py --pred_path predict_dev.json \
                   --dev_path dev/dev.json \
                   --db_path dev/dev_databases
"../.venv/bin/python" "eval.py" --pred_path "predict_dev_qwen_plus.json" --dev_path "dev/dev.json" --db_path "dev/dev_databases"
"""

import json
import sqlite3
import argparse
import time
from pathlib import Path
from collections import defaultdict


# ── Comparison: EXACT official logic ──────────────────────────────────────

def results_match(pred_results, gold_results) -> bool:
    """
    Official BIRD standard: set(pred) == set(gold)
    - Order ignored
    - Duplicates ignored (set deduplicates)
    This is EXACTLY what official evaluation.py does.
    """
    if pred_results is None and gold_results is None:
        return True
    if pred_results is None or gold_results is None:
        return False
    try:
        return set(pred_results) == set(gold_results)
    except TypeError:
        # Unhashable types (rare) — sort fallback
        try:
            return sorted(str(r) for r in pred_results) == \
                   sorted(str(r) for r in gold_results)
        except Exception:
            return False


# ── SQL execution ──────────────────────────────────────────────────────────

def execute_sql(db_path: str, sql: str, timeout: int = 30):
    """Execute SQL, return (results, error, time_seconds)"""
    t0 = time.time()
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        conn.close()
        return results, None, time.time() - t0
    except Exception as e:
        return None, str(e), 0.0


# ── Data loading ───────────────────────────────────────────────────────────

def load_predictions(pred_path: str) -> dict:
    """
    Accepts both:
      "0": "SELECT ...\t----- bird -----\tcalifornia_schools"
      "0": "SELECT ..."
    """
    with open(pred_path) as f:
        raw = json.load(f)

    predictions = {}
    for qid, value in raw.items():
        sql = str(value)
        if "\t----- bird -----\t" in sql:
            sql = sql.split("\t----- bird -----\t")[0]
        predictions[str(qid)] = sql.strip()
    return predictions


def load_dev_data(dev_path: str) -> list:
    with open(dev_path) as f:
        return json.load(f)


# ── Core evaluation ────────────────────────────────────────────────────────

def evaluate(pred_path, dev_path, db_root, limit=None, save_errors=True):

    predictions = load_predictions(pred_path)
    dev_data    = load_dev_data(dev_path)
    db_root     = Path(db_root)

    # Apply limit
    if limit:
        dev_data = dev_data[:limit]
        print(f"⚡ Quick mode: evaluating first {limit} questions only")

    total, correct = 0, 0
    exec_errors, wrong_results = 0, 0

    by_diff = defaultdict(lambda: {"total": 0, "correct": 0})
    by_db   = defaultdict(lambda: {"total": 0, "correct": 0})
    error_cases = []

    print(f"Evaluating {min(len(predictions), len(dev_data))} predictions...")
    print("-" * 60)

    t_start = time.time()

    for idx, item in enumerate(dev_data):
        qid        = str(idx)
        gold_sql   = item["SQL"]
        db_id      = item["db_id"]
        difficulty = item.get("difficulty", "simple")

        if qid not in predictions:
            continue

        total += 1
        pred_sql = predictions[qid]
        db_path  = str(db_root / db_id / f"{db_id}.sqlite")

        pred_res, pred_err, _ = execute_sql(db_path, pred_sql)
        gold_res, gold_err, _ = execute_sql(db_path, gold_sql)

        # Official: set-based
        if pred_err is None and gold_err is None:
            is_correct = results_match(pred_res, gold_res)
        else:
            is_correct = False

        if is_correct:
            correct += 1
        else:
            if pred_err is not None:
                exec_errors += 1
                etype = "execution_error"
            else:
                wrong_results += 1
                etype = "wrong_result"

            if save_errors:
                error_cases.append({
                    "qid":            qid,
                    "question":       item["question"],
                    "evidence":       item.get("evidence", ""),
                    "db_id":          db_id,
                    "difficulty":     difficulty,
                    "gold_sql":       gold_sql,
                    "pred_sql":       pred_sql,
                    "error_type":     etype,
                    "pred_error":     pred_err,
                    "gold_rows":      len(gold_res) if gold_res else 0,
                    "pred_rows":      len(pred_res) if pred_res else 0,
                })

        by_diff[difficulty]["total"]   += 1
        by_diff[difficulty]["correct"] += int(is_correct)
        by_db[db_id]["total"]          += 1
        by_db[db_id]["correct"]        += int(is_correct)

        # Progress every 100
        if (idx + 1) % 100 == 0:
            acc = correct / total * 100
            print(f"  [{idx+1:4d}]  running EX: {acc:.2f}%  "
                  f"({time.time()-t_start:.0f}s)")

    elapsed = time.time() - t_start
    acc_overall = correct / total * 100 if total else 0

    # ── Print ──────────────────────────────────────────────────────────────

    print()
    print("=" * 60)
    print("  BIRD Execution Accuracy (Official Standard)")
    if limit:
        print(f"  ⚡ Quick mode: first {limit} questions")
    print("=" * 60)
    print(f"  Questions evaluated : {total}")
    print(f"  Correct             : {correct}")
    print(f"  EX Accuracy         : {acc_overall:.2f}%")
    print(f"  Time                : {elapsed:.1f}s")
    print()

    diff_order = ["simple", "moderate", "challenging"]
    print(f"  {'Difficulty':<14} {'Correct':>8} {'Total':>8} {'EX%':>10}")
    print(f"  {'-'*44}")
    for diff in diff_order:
        if diff not in by_diff:
            continue
        d   = by_diff[diff]
        acc = d["correct"] / d["total"] * 100 if d["total"] else 0
        print(f"  {diff:<14} {d['correct']:>8} {d['total']:>8} {acc:>9.2f}%")

    print()
    print(f"  Error breakdown:")
    print(f"    Execution errors : {exec_errors} "
          f"({exec_errors/total*100:.1f}%)")
    print(f"    Wrong results    : {wrong_results} "
          f"({wrong_results/total*100:.1f}%)")

    if not limit:
        print()
        print(f"  {'Database':<28} {'Correct':>8} {'Total':>8} {'EX%':>10}")
        print(f"  {'-'*58}")
        for db_id in sorted(by_db):
            d   = by_db[db_id]
            acc = d["correct"] / d["total"] * 100 if d["total"] else 0
            print(f"  {db_id:<28} {d['correct']:>8} {d['total']:>8} {acc:>9.2f}%")

    print("=" * 60)

    return {
        "overall": {
            "total":       total,
            "correct":     correct,
            "EX_accuracy": round(acc_overall, 2),
        },
        "by_difficulty": {
            d: {
                "correct":  by_diff[d]["correct"],
                "total":    by_diff[d]["total"],
                "accuracy": round(by_diff[d]["correct"] /
                                  by_diff[d]["total"] * 100, 2)
                            if by_diff[d]["total"] else 0
            }
            for d in diff_order if d in by_diff
        },
        "error_breakdown": {
            "execution_errors": exec_errors,
            "wrong_results":    wrong_results,
        },
        "error_cases": error_cases,
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="BIRD EX evaluation — aligned with official standard"
    )
    p.add_argument("--pred_path", required=True,
                   help="predict_dev.json")
    p.add_argument("--dev_path",  required=True,
                   help="dev/dev.json")
    p.add_argument("--db_path",   required=True,
                   help="dev/dev_databases/")
    p.add_argument("--output",    default="eval_results.json",
                   help="output JSON path (default: eval_results.json)")
    p.add_argument("--limit",     type=int, default=None,
                   help="only evaluate first N questions (quick test)")
    p.add_argument("--no_errors", action="store_true",
                   help="skip saving error cases")
    args = p.parse_args()

    results = evaluate(
        pred_path   = args.pred_path,
        dev_path    = args.dev_path,
        db_root     = args.db_path,
        limit       = args.limit,
        save_errors = not args.no_errors,
    )

    out = args.output
    if args.limit:
        out = out.replace(".json", f"_first{args.limit}.json")

    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {out}")
    if not args.no_errors:
        print(f"  Error cases     : {len(results['error_cases'])}")


if __name__ == "__main__":
    main()