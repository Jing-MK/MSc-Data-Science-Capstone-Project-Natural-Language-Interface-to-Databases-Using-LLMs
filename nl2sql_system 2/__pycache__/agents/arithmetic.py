"""D8 — arithmetic / null handling: CAST (integer-division trap), NULL filter, evidence formula."""
import re
from agents.base import Agent
from engine.types import Candidate


class ArithmeticAgent(Agent):
    axis = "arithmetic"

    def enumerate(self, sql, ctx):
        out = []
        # integer division without CAST -> SQLite truncates to 0; propose a REAL cast
        if re.search(r"/", self._select_body(sql)) and not re.search(r"\bcast\s*\(", sql, re.I):
            m = re.search(r"([`\"\w.]+)\s*/\s*", self._select_body(sql))
            if m:
                num = m.group(1)
                alt = sql.replace(num + " /", f"CAST({num} AS REAL) /", 1) \
                      if num + " /" in sql else \
                      re.sub(re.escape(num) + r"\s*/", f"CAST({num} AS REAL) /", sql, count=1)
                if alt != sql:
                    out.append(Candidate(alt, self.axis,
                               "cast to REAL (avoid integer-division truncation)"))
        # toggle IS NOT NULL on an ORDER BY column (null stealing an extremum)
        if re.search(r"\border\s+by\b", sql, re.I) and not re.search(r"is\s+not\s+null", sql, re.I):
            m = re.search(r"(?i)order\s+by\s+([`\"\w.]+)", sql)
            if m and re.search(r"(?i)\bwhere\b", sql):
                col = m.group(1)
                alt = re.sub(r"(?i)(\bwhere\b)", rf"\1 {col} IS NOT NULL AND", sql, count=1)
                out.append(Candidate(alt, self.axis, f"require {col} IS NOT NULL"))
        return out
