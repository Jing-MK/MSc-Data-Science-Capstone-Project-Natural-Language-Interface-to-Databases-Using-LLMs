"""GroupByAgent: Detects and fixes unnecessary GROUP BY clauses.

Common error: Predicted SQL uses GROUP BY + aggregation when a simple ORDER BY would suffice.
Example: "Which district has the highest score?"
  Wrong: GROUP BY district ORDER BY AVG(score) LIMIT 1
  Right: ORDER BY score LIMIT 1
"""
import re
from agents.base import Agent
from engine.types import Candidate


class GroupByAgent(Agent):
    axis = "groupby"

    def enumerate(self, sql, ctx):
        """Generate candidates by removing unnecessary GROUP BY."""
        out = []

        # Check if SQL has GROUP BY
        if not re.search(r'\bGROUP\s+BY\b', sql, re.I):
            return out

        # Pattern 1: GROUP BY + aggregation + LIMIT 1 (looking for single max/min)
        # This often indicates we just want the top 1 row, not grouped aggregation
        if re.search(r'\bLIMIT\s+1\b', sql, re.I):
            # Check for aggregation functions in SELECT or ORDER BY
            has_agg_in_select = bool(re.search(
                r'\b(AVG|SUM|COUNT|MIN|MAX)\s*\(',
                sql,
                re.I
            ))

            if has_agg_in_select:
                # Try removing GROUP BY clause
                # Also need to remove aggregation wrapper from ORDER BY if present
                new_sql = sql

                # Remove GROUP BY clause
                new_sql = re.sub(
                    r'\s+GROUP\s+BY\s+[^\s]+(\s*,\s*[^\s]+)*',
                    '',
                    new_sql,
                    flags=re.I
                )

                # Remove AVG() wrapper from ORDER BY
                # Example: ORDER BY AVG(T2.score) -> ORDER BY T2.score
                new_sql = re.sub(
                    r'ORDER\s+BY\s+(AVG|MAX|MIN|SUM)\s*\(([^)]+)\)',
                    r'ORDER BY \2',
                    new_sql,
                    flags=re.I
                )

                if new_sql != sql:
                    out.append(Candidate(
                        new_sql, self.axis,
                        "remove GROUP BY (looking for single row, not grouped aggregation)"
                    ))

        # Pattern 2: GROUP BY without aggregation in SELECT
        # This is usually unnecessary
        select_match = re.search(r'(?is)^select\s+(.*?)\s+from\b', sql)
        if select_match:
            select_body = select_match.group(1)
            has_agg_in_select = bool(re.search(
                r'\b(AVG|SUM|COUNT|MIN|MAX|GROUP_CONCAT)\s*\(',
                select_body,
                re.I
            ))

            if not has_agg_in_select:
                # Remove GROUP BY - it's doing nothing useful
                new_sql = re.sub(
                    r'\s+GROUP\s+BY\s+[^\s]+(\s*,\s*[^\s]+)*',
                    '',
                    sql,
                    flags=re.I
                )

                if new_sql != sql:
                    out.append(Candidate(
                        new_sql, self.axis,
                        "remove GROUP BY (no aggregation in SELECT)"
                    ))

        return out
