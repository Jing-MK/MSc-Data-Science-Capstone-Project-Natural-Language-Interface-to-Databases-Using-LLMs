"""End-to-end demo of the full multi-agent + HITL system.
Uses an ORACLE user (picks the option matching a known gold result) so the
multi-round loop runs automatically — exactly Sphinteract's evaluation setup.
"""
from system import CorrectionSystem
from engine.execution import connect, execute, result_key

sys = CorrectionSystem("demo.sqlite")
gold_conn = connect("demo.sqlite")

def oracle(gold_sql):
    """Return a user() that picks the option whose result matches the gold query."""
    gcols, grows = execute(gold_conn, gold_sql)
    gkey = result_key(gcols, grows)
    def user(q):
        for i, opt in enumerate(q["options"]):
            if result_key(opt["columns"], opt["rows"]) == gkey:
                return i
        return 0   # fall back to 'keep current'
    return user

def show(opt):
    print(f"       [{opt['label']}] ({opt['n_rows']} rows): "
          f"{opt['columns']} e.g. {opt['rows'][0] if opt['rows'] else '-'}")

CASES = [
 dict(q="List the names of schools in Alameda county.",
      pred='SELECT "School Name" FROM schools WHERE County=\'Alameda\'',
      gold='SELECT School FROM schools WHERE County=\'Alameda\'', ev=""),
 dict(q="Schools in Alameda county (typo in value).",
      pred="SELECT School FROM schools WHERE County='alameda'",
      gold="SELECT School FROM schools WHERE County='Alameda'", ev=""),
 dict(q="List the distinct counties.",
      pred="SELECT DISTINCT County FROM schools",
      gold="SELECT DISTINCT County FROM schools", ev=""),
]

for i, c in enumerate(CASES, 1):
    print("\n" + "="*70)
    print(f"CASE {i}: {c['q']}")
    print(f"  predicted: {c['pred']}")
    final, cons, trans = sys.run(c["q"], c["pred"], evidence=c["ev"],
                                 user=oracle(c["gold"]),
                                 log=lambda m: print("  " + m))
    print(f"  FINAL SQL: {final}")
    ok = result_key(*execute(gold_conn, final)) == result_key(*execute(gold_conn, c["gold"]))
    print(f"  matches gold result? {'YES' if ok else 'no'}")
