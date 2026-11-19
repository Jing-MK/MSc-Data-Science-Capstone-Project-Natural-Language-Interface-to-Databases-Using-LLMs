"""D6 — WHERE predicates. Second largest class (57-63%)."""
import re
from agents.base import Agent
from engine.types import Candidate


class PredicateAgent(Agent):
    axis = "predicate"

    def enumerate(self, sql, ctx):
        out = []
        where = self._where_body(sql)
        if not where:
            return out
        # (a) value-domain fix: for each literal, try the real column domain
        for m in re.finditer(r'([`"\[]?[\w ]+[`"\]]?)\s*=\s*\'([^\']*)\'', where):
            col, val = m.group(1).strip().strip('`"[] '), m.group(2)
            bare = re.sub(r'^[\w]+\.', '', col)
            for table, actual in ctx.columns.get(bare.lower(), []):
                for dv in ctx.domain(table, actual):
                    if str(dv).lower() == val.lower() and str(dv) != val:
                        alt = sql.replace(f"'{val}'", f"'{dv}'")
                        out.append(Candidate(alt, self.axis,
                                   f"use stored value '{dv}' for {bare}"))
        # (b) drop an AND-condition (over-filtering)
        conj = re.split(r'(?i)\s+and\s+', where)
        if len(conj) > 1:
            for i in range(len(conj)):
                kept = " AND ".join(c for j, c in enumerate(conj) if j != i)
                alt = sql[:sql.lower().index('where')] + "WHERE " + kept
                out.append(Candidate(alt, self.axis, f"drop condition: {conj[i].strip()}"))
        return out
