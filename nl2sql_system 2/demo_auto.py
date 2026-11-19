"""AUTO demo that automatically selects the first option to show the system flow."""
from system import CorrectionSystem
from engine.execution import connect, execute, result_key


def render_table(cols, rows, width=22):
    """Pretty-print a result table (data only)."""
    if cols == "ERROR":
        return ["(query error)"]
    def cell(v):
        s = "" if v is None else str(v)
        return s[:width]
    out = []
    header = " | ".join(f"{cell(c):<{width}}" for c in cols)
    out.append(header)
    out.append("-" * len(header))
    for r in rows[:6]:
        out.append(" | ".join(f"{cell(v):<{width}}" for v in r))
    if len(rows) > 6:
        out.append(f"... ({len(rows)} rows total)")
    return out


def auto_user(q):
    """Automatically show all options and choose the first one."""
    print("\n  " + "─"*64)
    print("  🤔 The system detected ambiguity and presents options:")
    print("  " + "─"*64)

    for i, opt in enumerate(q["options"]):
        letter = chr(65 + i)
        print(f"\n  Option {letter}   ({opt['n_rows']} rows)")
        for ln in render_table(opt["columns"], opt["rows"]):
            print("    " + ln)

    # Automatically select the first option
    print("\n  ✅ Auto-selecting Option A")
    return 0


def main():
    sys = CorrectionSystem("demo.sqlite")
    gold = connect("demo.sqlite")

    CASES = [
     ("List the names of schools in Alameda county.",
      'SELECT "School Name" FROM schools WHERE County=\'Alameda\''),
     ("Schools in Alameda county.",
      "SELECT School FROM schools WHERE County='alameda'"),
    ]

    for q, pred in CASES:
        print("\n" + "="*68)
        print(f"QUESTION: {q}")
        print(f"PREDICTED SQL: {pred}")
        print("─"*68)

        final, cons, trans = sys.run(q, pred, user=auto_user,
                                     log=lambda m: print(f"  [LOG] {m}"))

        print("\n  ✅ Final SQL after correction:")
        print(f"     {final}")

        cols, rows = execute(gold, final)
        print("\n  📊 Final answer:")
        for ln in render_table(cols, rows):
            print("     " + ln)

        if cons:
            print(f"\n  📝 Decisions recorded: {'; '.join(c.description for c in cons)}")

        print()

if __name__ == "__main__":
    main()
