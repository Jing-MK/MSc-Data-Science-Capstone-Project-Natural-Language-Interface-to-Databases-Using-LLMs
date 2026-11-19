"""PRESENTATION demo with detailed step-by-step output for live demos."""
from system import CorrectionSystem
from engine.execution import connect, execute
import time


def render_table(cols, rows, width=22):
    """Pretty-print a result table."""
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


def presentation_user(q):
    """Interactive user with detailed presentation output."""
    print("\n" + "  " + "🔍 " + "="*62)
    print("  " + "  SYSTEM DETECTED AMBIGUITY - User Input Required")
    print("  " + "="*65 + "\n")

    print("  💭 The system found multiple valid interpretations.")
    print("  📊 Showing actual DATA from each interpretation:\n")

    for i, opt in enumerate(q["options"]):
        letter = chr(65 + i)
        print(f"  ┌─ Option {letter} " + "─"*52 + "┐")
        print(f"  │  {opt['n_rows']} rows returned")
        for ln in render_table(opt["columns"], opt["rows"]):
            print(f"  │  {ln}")
        print("  └" + "─"*63 + "┘\n")

    print("  " + "─"*65)
    while True:
        ans = input("  👉 Your choice (letter): ").strip().upper()
        if ans and ord(ans) - 65 in range(len(q["options"])):
            choice_idx = ord(ans) - 65
            print(f"\n  ✅ You selected: Option {ans}")
            print(f"     ({q['options'][choice_idx]['n_rows']} rows with columns: {', '.join(q['options'][choice_idx]['columns'])})")
            return choice_idx
        print("  ⚠️  Please type one of the option letters (A, B, etc.)")


def main():
    print("\n" + "="*70)
    print("  🎯 NL2SQL HUMAN-IN-THE-LOOP CORRECTION SYSTEM")
    print("  " + "="*68)
    print("\n  This demo shows how the system handles SQL ambiguities")
    print("  by asking users to choose between actual result tables.\n")
    print("="*70 + "\n")

    sys = CorrectionSystem("demo.sqlite")
    gold = connect("demo.sqlite")

    CASES = [
        ("List the names of schools in Alameda county.",
         'SELECT "School Name" FROM schools WHERE County=\'Alameda\''),
        ("Schools in Alameda county.",
         "SELECT School FROM schools WHERE County='alameda'"),
    ]

    for case_num, (question, predicted_sql) in enumerate(CASES, 1):
        print("\n" + "━"*70)
        print(f"  📝 CASE {case_num}")
        print("━"*70)
        print(f"\n  ❓ QUESTION: {question}")
        print(f"\n  🤖 PREDICTED SQL (from NL2SQL model):")
        print(f"      {predicted_sql}")
        print("\n  ⚙️  Checking SQL correctness...")

        # Custom logger for presentation
        def log(msg):
            if "ASK" in msg:
                print(f"\n  ⚠️  {msg}")
            elif "AUTOFIX" in msg:
                print(f"\n  ✨ {msg}")
            elif "user chose" in msg:
                print(f"  💾 Decision recorded: {msg.split('user chose: ')[1]}")
            elif "ABSTAIN" in msg:
                print(f"  ✓  {msg}")

        final, cons, trans = sys.run(question, predicted_sql,
                                     user=presentation_user,
                                     log=log)

        print("\n  " + "─"*66)
        print("  ✅ FINAL CORRECTED SQL:")
        print(f"      {final}")

        cols, rows = execute(gold, final)
        print("\n  📊 FINAL RESULT TABLE:")
        for ln in render_table(cols, rows):
            print("      " + ln)

        if cons:
            print(f"\n  📝 System learned: {', '.join(c.description for c in cons)}")

        print()

        if case_num < len(CASES):
            input("  Press Enter to continue to next case...")

    print("\n" + "="*70)
    print("  🎉 DEMO COMPLETED!")
    print("  " + "="*68)
    print("\n  Key takeaways:")
    print("  • System detects ambiguities before execution")
    print("  • Shows ACTUAL DATA instead of SQL to users")
    print("  • Auto-fixes simple errors (like case sensitivity)")
    print("  • Only asks users when truly ambiguous")
    print("  • Learns from user choices for future queries")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
