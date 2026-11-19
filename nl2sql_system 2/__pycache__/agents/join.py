"""D1 — tables / join paths, over the foreign-key graph (29%)."""
import re
from agents.base import Agent
from engine.types import Candidate


class JoinAgent(Agent):
    axis = "join"

    def enumerate(self, sql, ctx):
        out = []
        used = set(re.findall(r'(?:from|join)\s+[`"\[]?(\w+)', sql, re.I))
        # propose joining a table reachable by FK from a used table but not yet joined
        for t in list(used):
            for from_col, ref_table, ref_col in ctx.foreign_keys(t):
                if ref_table.lower() not in {u.lower() for u in used}:
                    note = f"also join {ref_table} on {t}.{from_col}={ref_table}.{ref_col}"
                    # structural suggestion only; regeneration realises it (see hitl)
                    out.append(Candidate(sql, self.axis, note))
        return out
