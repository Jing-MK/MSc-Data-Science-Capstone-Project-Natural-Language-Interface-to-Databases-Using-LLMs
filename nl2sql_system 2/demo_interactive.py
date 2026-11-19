"""INTERACTIVE demo for the live presentation.

The user is shown competing ANSWER TABLES and types a letter to choose.
No SQL is shown to the user — only the resulting data tables.
"""
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


def interactive_user(q):
    """Show answer tables side by side; read the user's choice from the keyboard."""
    print("\n  " + "─"*64)
    print("  🤔 The system is unsure which answer you want. Please choose:")
    print("  " + "─"*64)
    blocks = []
    for i, opt in enumerate(q["options"]):
        letter = chr(65 + i)
        lines = [f"  Option {letter}   ({opt['n_rows']} rows)"]
        lines += ["    " + ln for ln in render_table(opt["columns"], opt["rows"])]
        blocks.append(lines)
    for b in blocks:                       # print each option's table
        print(); 
        for ln in b: print(ln)
    print()
    while True:
        ans = input("  Your choice (letter): ").strip().upper()
        if ans and ord(ans) - 65 in range(len(q["options"])):
            return ord(ans) - 65
        print("  Please type one of the option letters.")


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
        print("(the predicted SQL is hidden from the user; it is being checked...)")
        final, cons, trans = sys.run(q, pred, user=interactive_user,
                                     log=lambda m: None)
        print("\n  ✅ Final answer the user confirmed:")
        cols, rows = execute(gold, final)
        for ln in render_table(cols, rows):
            print("     " + ln)
        if cons:
            print("  (decisions recorded:", "; ".join(c.description for c in cons), ")")

if __name__ == "__main__":
    main()
