"""RankAgent: Detects when RANK() window function should be added.

Common error: Question asks to "rank" items, but SQL only uses ORDER BY.
Example: "Rank schools by their average score"
  Wrong: SELECT school, score FROM ... ORDER BY score DESC
  Right: SELECT school, score, RANK() OVER (ORDER BY score DESC) AS rank FROM ...
"""
import re
from agents.base import Agent
from engine.types import Candidate


class RankAgent(Agent):
    axis = "rank"

    def enumerate(self, sql, ctx):
        """Generate candidates by adding RANK() window function when appropriate."""
        out = []

        # Only trigger if question mentions "rank"
        question_lower = ctx.question.lower() if ctx.question else ""
        if 'rank' not in question_lower:
            return out

        # Check if SQL already has RANK()
        if re.search(r'\bRANK\s*\(', sql, re.I):
            return out

        # Check if SQL has ORDER BY (needed for ranking)
        order_match = re.search(r'\bORDER\s+BY\s+([^\s]+(?:\s+(?:ASC|DESC))?)', sql, re.I)
        if not order_match:
            return out

        order_clause = order_match.group(1)

        # Extract the ORDER BY expression and direction
        order_parts = re.match(r'([^\s]+)\s*(ASC|DESC)?', order_clause, re.I)
        if not order_parts:
            return out

        order_expr = order_parts.group(1)
        order_dir = order_parts.group(2) if order_parts.group(2) else 'ASC'

        # Add RANK() OVER (ORDER BY ...) to SELECT clause
        select_match = re.search(r'(?is)^(SELECT\s+)(.*?)(\s+FROM\b)', sql)
        if not select_match:
            return out

        prefix = select_match.group(1)
        select_cols = select_match.group(2)
        from_clause = select_match.group(3)

        # Add RANK() as a new column
        rank_expr = f"RANK() OVER (ORDER BY {order_expr} {order_dir})"

        # Try to infer a good column name from the ORDER BY expression
        # e.g., "AvgScrWrite" -> "WritingScoreRank"
        if 'write' in order_expr.lower() or 'writing' in order_expr.lower():
            rank_name = "WritingScoreRank"
        elif 'read' in order_expr.lower() or 'reading' in order_expr.lower():
            rank_name = "ReadingScoreRank"
        elif 'math' in order_expr.lower():
            rank_name = "MathScoreRank"
        elif 'score' in order_expr.lower():
            rank_name = "ScoreRank"
        else:
            rank_name = "Rank"

        new_select = f"{select_cols}, {rank_expr} AS {rank_name}"
        new_sql = f"{prefix}{new_select}{from_clause}" + sql[select_match.end():]

        out.append(Candidate(
            new_sql, self.axis,
            f"add RANK() window function (question asks to 'rank')"
        ))

        return out
