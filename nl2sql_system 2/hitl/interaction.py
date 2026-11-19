"""Multi-round human-in-the-loop correction.

Each round:
  probe -> if AUTOFIX apply & re-probe; if ASK present result tables to the user
  record the answer as a Constraint, apply it, re-probe.
Stops when the result clusters collapse to one (deterministic) or the round
budget (default 4, justified empirically) is reached.

The `user` argument is a callable(question_dict) -> chosen_index, so the same
loop drives a human UI, an oracle simulator, or the CLI demo.
"""
from engine.orchestrator import probe
from engine.types import Constraint


def format_question(decision):
    """Turn an ASK decision into options = ANSWER TABLES (never SQL)."""
    options = []
    for cl in decision.clusters:
        rep = cl.representative
        label = rep.note if rep.axis != "baseline" else "keep current answer"
        options.append({
            "label": label,
            "axis": rep.axis,
            "n_rows": cl.n_rows,
            "columns": rep.cols,
            "rows": rep.rows[:8] if rep.rows else [],
            "sql": rep.sql,                 # kept internally, NOT shown to the user
        })
    return {"axis": decision.axis,
            "prompt": "Which answer did you intend?",
            "options": options}


def correct(conn, base_sql, agents, ctx, user, max_rounds=4, log=None):
    """Run the HITL loop. Returns (final_sql, constraints, transcript)."""
    sql = base_sql
    constraints = []
    transcript = []
    resolved = set()

    for rnd in range(1, max_rounds + 1):
        decision = probe(conn, sql, agents, ctx, resolved_axes=resolved)
        transcript.append((rnd, decision.action, decision.reason))
        if log:
            log(f"round {rnd}: {decision.action} — {decision.reason}")

        if decision.action == "ABSTAIN":
            break                                   # deterministic stop: clusters collapsed

        if decision.action == "AUTOFIX":
            sql = decision.chosen.sql
            resolved.add(decision.axis)
            constraints.append(Constraint(decision.axis,
                               decision.chosen.note, sql))
            continue                                # re-probe: a fix may expose/remove another axis

        if decision.action == "ASK":
            q = format_question(decision)
            idx = user(q)                           # UI / oracle / CLI returns an option index
            chosen = q["options"][idx]
            sql = chosen["sql"]
            resolved.add(decision.axis)
            constraints.append(Constraint(chosen["axis"], chosen["label"], sql))
            if log:
                log(f"   user chose: {chosen['label']} ({chosen['n_rows']} rows)")
            continue

    return sql, constraints, transcript
