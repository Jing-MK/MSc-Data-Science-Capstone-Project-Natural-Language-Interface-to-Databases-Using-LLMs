"""PercentageAgent: Detects and fixes * 100 / * 100.0 issues in percentage calculations.

Common error: Predicted SQL has * 100 or * 100.0, but gold SQL doesn't (or vice versa).
This agent proposes removing or adding * 100 based on context.
"""
import re
from agents.base import Agent
from engine.types import Candidate


class PercentageAgent(Agent):
    axis = "percentage"

    def enumerate(self, sql, ctx):
        """Generate candidates by adding/removing * 100 from arithmetic expressions."""
        out = []

        # Pattern 1: SQL has * 100 or * 100.0 - try removing it
        if re.search(r'\*\s*100(\.0)?', sql):
            # Remove * 100.0 or * 100
            new_sql = re.sub(r'\s*\*\s*100(\.0)?', '', sql)
            out.append(Candidate(
                new_sql, self.axis,
                "remove * 100 (percentage scaling)"
            ))

        # Pattern 2: SQL has division but no * 100 - try adding it
        # Only if question mentions "percent" or evidence mentions "percent"
        question_lower = ctx.question.lower() if ctx.question else ""
        evidence_lower = ctx.evidence.lower() if ctx.evidence else ""

        has_percent_context = any(word in question_lower + evidence_lower
                                   for word in ['percent', 'percentage', '%', 'rate'])

        # Find division expressions in SELECT clause
        select_match = re.search(r'(?is)^select\s+(.*?)\s+from\b', sql)
        if select_match and has_percent_context:
            select_body = select_match.group(1)

            # Check if there's division without * 100
            if '/' in select_body and not re.search(r'\*\s*100', sql):
                # Add * 100.0 to the division expression
                # Simple approach: wrap first division expression
                division_pattern = r'(\([^)]*\/[^)]*\)|[^,\s]+\s*\/\s*[^,\s]+)'

                def add_percentage(match):
                    expr = match.group(1)
                    # Don't modify if already has * 100
                    if '* 100' in expr:
                        return expr
                    return f"({expr}) * 100.0"

                new_select = re.sub(division_pattern, add_percentage, select_body, count=1)
                if new_select != select_body:
                    new_sql = sql.replace(select_body, new_select, 1)
                    out.append(Candidate(
                        new_sql, self.axis,
                        "add * 100.0 for percentage calculation"
                    ))

        return out
