"""Base class for decision-point agents.

Each agent OWNS one SQL decision point and exposes exactly one capability:
    enumerate(sql, ctx) -> list[Candidate]
proposing alternative queries that differ from `sql` only along its own clause.

An agent NEVER diagnoses whether its clause is wrong (impossible at run time
without a gold query); it only proposes what else the clause could be.
"""
import re
from engine.types import Candidate


class Agent:
    axis = "base"

    def enumerate(self, sql, ctx):
        raise NotImplementedError

    # ---- shared helpers ----
    @staticmethod
    def _has(sql, pat):
        return bool(re.search(pat, sql, re.I))

    @staticmethod
    def _select_body(sql):
        m = re.search(r"(?is)\bselect\b(.*?)\bfrom\b", sql)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _where_body(sql):
        m = re.search(r"(?is)\bwhere\b(.*?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)", sql)
        return m.group(1).strip() if m else ""
