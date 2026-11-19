"""Execute candidates, cluster by result, and triage: ABSTAIN / AUTOFIX / ASK.

This is the heart of Chapter 5. The triage decision rests only on observed
execution behaviour — never on a model judging correctness, and never on a gold
query.
"""
import re
from engine.execution import execute, result_key, is_empty, is_error
from engine.types import Candidate, Cluster, Decision


def _evidence_formula_ok(sql, evidence):
    """Objective signal: does the query implement a '* 100' percentage when the
    evidence defines one? (A simple, checkable instance of evidence conformance.)"""
    if not evidence:
        return None
    ev_pct = bool(re.search(r"%|percent|\*\s*100", evidence, re.I))
    sql_pct = bool(re.search(r"\*\s*100", sql))
    return ev_pct == sql_pct


def probe(conn, base_sql, agents, ctx, resolved_axes=None):
    """Run all agents, execute every candidate, cluster, and triage."""
    base = Candidate(base_sql, "baseline", "current query")
    base.cols, base.rows = execute(conn, base_sql)
    base.key = result_key(base.cols, base.rows)
    candidates = [base]

    resolved_axes = resolved_axes or set()
    for agent in agents:
        if agent.axis in resolved_axes:      # user already decided this clause
            continue
        for c in agent.enumerate(base_sql, ctx):
            if c.sql == base_sql:            # structural-only suggestion (e.g. join) — keep note, skip exec dup
                c.key = base.key; c.cols, c.rows = base.cols, base.rows
            else:
                try:
                    c.cols, c.rows = execute(conn, c.sql)
                    c.key = result_key(c.cols, c.rows)
                except Exception:
                    # Execution error - mark as ERROR
                    c.key = ('ERROR',)
                    c.cols, c.rows = [], []
            candidates.append(c)

    # cluster by execution result
    buckets = {}
    for c in candidates:
        buckets.setdefault(c.key, []).append(c)
    clusters = [Cluster(k, ms) for k, ms in buckets.items()]
    answer_clusters = [cl for cl in clusters if not is_error(cl.key)]

    # ---- TRIAGE ----
    # 1) single result cluster -> no genuine divergence -> ABSTAIN
    if len(answer_clusters) <= 1:
        return Decision("ABSTAIN", clusters=clusters,
                        reason="all candidates agree; nothing to change")

    # 2) objective signal selects exactly one cluster -> AUTOFIX
    nonempty = [cl for cl in answer_clusters if not is_empty(cl.key)]
    if len(nonempty) == 1:
        return Decision("AUTOFIX", axis=nonempty[0].representative.axis,
                        clusters=clusters, chosen=nonempty[0].representative,
                        reason="only one candidate returns a non-empty result")
    ev_ok = [cl for cl in answer_clusters
             if _evidence_formula_ok(cl.representative.sql, ctx.evidence) is True]
    if ctx.evidence and len(ev_ok) == 1 and len(answer_clusters) > 1:
        return Decision("AUTOFIX", axis=ev_ok[0].representative.axis,
                        clusters=clusters, chosen=ev_ok[0].representative,
                        reason="only one candidate satisfies the evidence formula")

    # 3) genuine, intent-dependent divergence -> ASK ONE axis (chosen by info-gain).
    #    Present only that axis's result options plus the baseline, so each round
    #    asks a single, clean question.
    ask_axis = _choose_axis_by_infogain(answer_clusters, base.key)
    if ask_axis is None:
        return Decision("ABSTAIN", clusters=clusters,
                        reason="no contrasting answers across axes")
    # keep the baseline answer + each distinct answer produced along the chosen axis
    kept, seen = [], set()
    # baseline cluster first
    for cl in answer_clusters:
        if cl.key == base.key and cl.key not in seen:
            kept.append(cl); seen.add(cl.key)
    for cl in answer_clusters:
        if cl.key in seen:
            continue
        if any(m.axis == ask_axis for m in cl.members):
            kept.append(cl); seen.add(cl.key)
    if len(kept) < 2:
        return Decision("ABSTAIN", clusters=clusters,
                        reason="no contrasting answers on the selected axis")
    return Decision("ASK", axis=ask_axis, clusters=kept,
                    reason="results diverge and no objective signal selects one")


def _choose_axis_by_infogain(answer_clusters, base_key):
    """EIG proxy in RESULT space: prefer the axis that yields the most distinct
    result clusters differing from the baseline — i.e. the axis that most reduces
    uncertainty about the intended answer."""
    from collections import defaultdict
    axis_keys = defaultdict(set)
    for cl in answer_clusters:
        for m in cl.members:
            if m.axis != "baseline" and cl.key != base_key:
                axis_keys[m.axis].add(cl.key)
    if not axis_keys:
        return None
    # axis with the most distinct diverging result clusters
    return max(axis_keys.items(), key=lambda kv: len(kv[1]))[0]
