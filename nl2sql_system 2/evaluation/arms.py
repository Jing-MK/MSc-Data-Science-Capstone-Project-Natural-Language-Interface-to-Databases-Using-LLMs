"""The three correction strategies (arms) compared in the evaluation."""
from engine.orchestrator import probe
from engine.context import Context
from engine.execution import execute, result_key
from hitl.interaction import correct


def arm_none(conn, question, pred_sql, evidence, agents, oracle_key):
    """Baseline: no correction."""
    return pred_sql, 0


def arm_fix_always(conn, question, pred_sql, evidence, agents, oracle_key):
    """SQLENS-style: whenever candidates diverge, auto-pick (here: the first
    non-baseline diverging cluster) — never asks the user."""
    ctx = Context(conn, evidence=evidence, question=question)
    sql = pred_sql
    for _ in range(4):
        d = probe(conn, sql, agents, ctx)
        if d.action == "ABSTAIN":
            break
        if d.action == "AUTOFIX":
            sql = d.chosen.sql; continue
        # ASK -> but fix-always never asks: take the first diverging option
        opts = [cl.representative for cl in d.clusters
                if cl.representative.axis != "baseline"]
        if not opts:
            break
        sql = opts[0].sql
    return sql, 0


def arm_ask_always(conn, question, pred_sql, evidence, agents, oracle_key, user):
    """Sphinteract-style: ask the user on every divergence (no auto-fix triage).
    Counts one question per ASK round."""
    ctx = Context(conn, evidence=evidence, question=question)
    sql = pred_sql
    q = 0
    resolved = set()
    for _ in range(4):
        d = probe(conn, sql, agents, ctx, resolved_axes=resolved)
        if d.action == "ABSTAIN":
            break
        # treat AUTOFIX as something ask-always would also put to the user
        from hitl.interaction import format_question
        if d.action in ("ASK", "AUTOFIX"):
            if d.action == "AUTOFIX":
                # reconstruct a question over the clusters so the user decides
                from engine.types import Decision
                d = Decision("ASK", axis=d.axis, clusters=d.clusters)
            question_dict = format_question(d)
            if len(question_dict["options"]) < 2:
                break
            q += 1
            idx = user(question_dict)
            sql = question_dict["options"][idx]["sql"]
            resolved.add(d.axis)
    return sql, q


def arm_triage(conn, question, pred_sql, evidence, agents, oracle_key, user):
    """Our framework: auto-fix where a signal decides, ask only where needed."""
    from hitl.interaction import correct
    ctx = Context(conn, evidence=evidence, question=question)
    # wrap user to count questions
    counter = {"q": 0}
    def counting_user(qd):
        counter["q"] += 1
        return user(qd)
    final, cons, trans = correct(conn, pred_sql, agents, ctx,
                                 user=counting_user, max_rounds=4)
    return final, counter["q"]
