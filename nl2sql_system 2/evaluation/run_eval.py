"""Run the three-arm evaluation and report N_fix / N_break / questions.

Usage (on the real benchmark):
  python3 -m evaluation.run_eval --cases cases.json --dbroot /path/to/dev_databases

`cases.json` is a list of records:
  {"db_id","question","evidence","predicted_sql","gold_sql"}
Each database is opened at  <dbroot>/<db_id>/<db_id>.sqlite  (BIRD layout).

With no --cases it runs a small built-in demo on demo.sqlite so the pipeline
can be checked end-to-end without the full benchmark.
"""
import argparse, json, os
from system import default_agents
from engine.execution import connect, execute, result_key
from evaluation.metrics import EvalResult
from evaluation import arms


def make_oracle(conn, gold_sql):
    gkey = result_key(*execute(conn, gold_sql))
    def user(qd):
        for i, opt in enumerate(qd["options"]):
            if result_key(opt["columns"], opt["rows"]) == gkey:
                return i
        return 0
    return user, gkey


def correct_before(conn, pred_sql, gkey):
    return result_key(*execute(conn, pred_sql)) == gkey


def evaluate(cases, open_db):
    agents = default_agents()
    arms_def = {
        "no-correction": lambda c, conn, u, gk: arms.arm_none(conn, c["question"], c["predicted_sql"], c.get("evidence",""), agents, gk),
        "fix-always":    lambda c, conn, u, gk: arms.arm_fix_always(conn, c["question"], c["predicted_sql"], c.get("evidence",""), agents, gk),
        "ask-always":    lambda c, conn, u, gk: arms.arm_ask_always(conn, c["question"], c["predicted_sql"], c.get("evidence",""), agents, gk, u),
        "triage (ours)": lambda c, conn, u, gk: arms.arm_triage(conn, c["question"], c["predicted_sql"], c.get("evidence",""), agents, gk, u),
    }
    results = {name: EvalResult() for name in arms_def}

    for c in cases:
        conn = open_db(c["db_id"])
        if conn is None:
            continue
        user, gkey = make_oracle(conn, c["gold_sql"])
        before_ok = correct_before(conn, c["predicted_sql"], gkey)
        for name, fn in arms_def.items():
            R = results[name]
            final_sql, q = fn(c, conn, user, gkey)
            after_ok = result_key(*execute(conn, final_sql)) == gkey
            R.n_total += 1
            R.correct_before += int(before_ok)
            R.correct_after += int(after_ok)
            R.questions += q
            if not before_ok and after_ok: R.n_fix += 1
            if before_ok and not after_ok: R.n_break += 1
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases"); ap.add_argument("--dbroot")
    a = ap.parse_args()

    if a.cases:
        cases = json.load(open(a.cases))
        def open_db(db_id):
            p = os.path.join(a.dbroot, db_id, f"{db_id}.sqlite")
            return connect(p) if os.path.exists(p) else None
    else:
        # built-in demo
        cases = [
          dict(db_id="demo", question="names of schools in Alameda",
               evidence="", predicted_sql='SELECT "School Name" FROM schools WHERE County=\'Alameda\'',
               gold_sql='SELECT School FROM schools WHERE County=\'Alameda\''),
          dict(db_id="demo", question="schools in Alameda (typo)",
               evidence="", predicted_sql="SELECT School FROM schools WHERE County='alameda'",
               gold_sql="SELECT School FROM schools WHERE County='Alameda'"),
          dict(db_id="demo", question="distinct counties",
               evidence="", predicted_sql="SELECT DISTINCT County FROM schools",
               gold_sql="SELECT DISTINCT County FROM schools"),
          dict(db_id="demo", question="a correct query (must not be broken)",
               evidence="", predicted_sql="SELECT School FROM schools WHERE County='Fresno'",
               gold_sql="SELECT School FROM schools WHERE County='Fresno'"),
        ]
        open_db = lambda db_id: connect("demo.sqlite")

    results = evaluate(cases, open_db)
    print("="*60); print(f"THREE-ARM EVALUATION  ({results['triage (ours)'].n_total} cases)"); print("="*60)
    for name, R in results.items():
        R.report(name)
    print("\n" + "-"*60)
    print("Read: a good triage matches ask-always on EX with FEWER questions,")
    print("and keeps N_break at or below fix-always.")

if __name__ == "__main__":
    main()
