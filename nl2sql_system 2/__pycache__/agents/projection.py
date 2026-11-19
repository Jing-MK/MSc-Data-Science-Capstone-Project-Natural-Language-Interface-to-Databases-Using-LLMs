"""D2 — projected columns (SELECT). The largest error class (62-75%)."""
import re
from agents.base import Agent
from engine.types import Candidate
from difflib import SequenceMatcher


class ProjectionAgent(Agent):
    axis = "projection"

    def _swap_token(self, sql, frm, to):
        """Replace a column token in bare / "quoted" / `backtick` form, longest-safe."""
        for lq, rq in [('"', '"'), ('`', '`')]:
            pat = re.escape(lq + frm + rq)
            if re.search(pat, sql):
                return re.sub(pat, lq + to + rq, sql)
        # bare: whole-token only, so "School" does not touch "School Name"
        pat = r'(?<![\w"`])' + re.escape(frm) + r'(?![\w"` ])'
        if re.search(pat, sql):
            return re.sub(pat, to if re.match(r'^\w+$', to) else f'"{to}"', sql)
        return sql

    def _similar_columns(self, col, ctx, thresh=0.6):
        """Schema columns whose names are lexically close to `col`."""
        out = []
        cl = col.lower().strip('`" ')
        for other_lower, places in ctx.columns.items():
            if other_lower == cl:
                continue
            ratio = SequenceMatcher(None, cl, other_lower).ratio()
            shares = cl in other_lower or other_lower in cl
            if ratio >= thresh or shares:
                out.append(places[0][1])   # actual name
        return out[:4]

    def enumerate(self, sql, ctx):
        out = []
        body = self._select_body(sql)
        projected = [p.strip() for p in re.split(r",(?![^(]*\))", body)]
        for col in projected:
            name = re.sub(r"(?i)\s+as\s+[`\"\w]+$", "", col).strip()
            bare = re.sub(r'^[\w]+\.', '', name).strip('`" ')
            if not re.match(r'^[`"\w .]+$', bare):
                continue
            for alt in self._similar_columns(bare, ctx):
                newsql = self._swap_token(sql, bare, alt)
                if newsql != sql:
                    out.append(Candidate(newsql, self.axis,
                               f"project '{alt}' instead of '{bare}'"))
        # also offer LLM-proposed candidates if a proposer is wired in
        if ctx.llm_propose:
            for s, note in ctx.llm_propose(sql, self.axis):
                out.append(Candidate(s, self.axis, note))
        return out
