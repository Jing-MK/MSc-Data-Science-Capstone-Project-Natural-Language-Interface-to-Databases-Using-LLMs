"""D3 distinct, D4 aggregate, D5 group-by, D7 order/limit — small enumerable sets."""
import re
from agents.base import Agent
from engine.types import Candidate


class DistinctAgent(Agent):
    axis = "distinct"
    def enumerate(self, sql, ctx):
        if re.search(r"\bselect\s+distinct\b", sql, re.I):
            return [Candidate(re.sub(r"(?i)\bselect\s+distinct\b", "SELECT", sql),
                              self.axis, "remove DISTINCT")]
        return [Candidate(re.sub(r"(?i)\bselect\b", "SELECT DISTINCT", sql, count=1),
                          self.axis, "add DISTINCT")]


class AggregateAgent(Agent):
    axis = "aggregate"
    def enumerate(self, sql, ctx):
        out = []
        if re.search(r"\bcount\s*\(\s*(?!distinct)", sql, re.I):
            out.append(Candidate(
                re.sub(r"(?i)\bcount\s*\(\s*", "COUNT(DISTINCT ", sql, count=1),
                self.axis, "COUNT distinct instead of COUNT all"))
        if re.search(r"\bcount\s*\(\s*distinct", sql, re.I):
            out.append(Candidate(
                re.sub(r"(?i)\bcount\s*\(\s*distinct\s+", "COUNT(", sql, count=1),
                self.axis, "COUNT all instead of COUNT distinct"))
        return out


class OrderAgent(Agent):
    axis = "order"
    def enumerate(self, sql, ctx):
        out = []
        if re.search(r"\border\s+by\b", sql, re.I):
            if re.search(r"\bdesc\b", sql, re.I):
                out.append(Candidate(re.sub(r"(?i)\bdesc\b", "ASC", sql),
                                     self.axis, "sort ascending instead of descending"))
            else:
                out.append(Candidate(re.sub(r"(?i)(order\s+by\s+[^;]+?)(\s+limit|\s*$)",
                           r"\1 DESC\2", sql, count=1),
                           self.axis, "sort descending instead of ascending"))
        return out
