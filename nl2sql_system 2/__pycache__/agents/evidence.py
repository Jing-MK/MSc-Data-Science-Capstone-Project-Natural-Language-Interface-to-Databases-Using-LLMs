"""Evidence Agent - 检查 SQL 是否实现了 Evidence 中的要求

BIRD 数据集中 90% 的案例都有 Evidence 提示。
Evidence 包含：
1. 列名映射 (用 backticks 标记)
2. 条件定义 ("X refers to column = 'value'")
3. 计算公式 ("Rate = A / B")
4. 数据说明

这个 Agent 检查 SQL 是否正确使用了 Evidence 中的信息。
"""
import re
from agents.base import Agent
from engine.types import Candidate


class EvidenceAgent(Agent):
    axis = "evidence"

    def enumerate(self, sql, ctx):
        if not ctx.evidence:
            return []

        out = []
        evidence = ctx.evidence

        # ===== 1. 检查 Evidence 中提到的列是否在 SQL 中 =====
        # Evidence 中用 backticks 标记的列名: `Column Name`
        evidence_columns = re.findall(r'`([^`]+)`', evidence)

        if evidence_columns:
            sql_lower = sql.lower()
            for col in evidence_columns:
                col_variations = [
                    col,
                    f'"{col}"',
                    f'`{col}`',
                    col.replace(' ', '_'),
                    col.replace('_', ' ')
                ]

                # 检查这个列是否在 SQL 中
                found = any(var.lower() in sql_lower for var in col_variations)

                if not found:
                    # 提议添加这个列到 SELECT
                    # 简单策略：在第一个逗号后添加
                    select_match = re.search(r'(?is)^(select\s+)(.*?)(\s+from\b)', sql)
                    if select_match:
                        prefix, existing_cols, from_clause = select_match.groups()
                        # 添加列（带引号以处理空格）
                        new_cols = f"{existing_cols}, `{col}`" if existing_cols.strip() != '*' else f"`{col}`"
                        new_sql = f"{prefix}{new_cols}{from_clause}" + sql[select_match.end():]
                        out.append(Candidate(
                            new_sql, self.axis,
                            f"add column '{col}' mentioned in evidence"
                        ))

        # ===== 2. 检查 Evidence 中定义的条件 =====
        # Pattern: "X refers to column = 'value'"
        # Pattern: "X means column = 'value'"
        condition_patterns = [
            r"(\w+)\s+refers\s+to\s+([`\w\s]+)\s*=\s*['\"]([^'\"]+)['\"]",
            r"(\w+)\s+means\s+([`\w\s]+)\s*=\s*['\"]([^'\"]+)['\"]",
            r"where\s+([`\w\s]+)\s*=\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in condition_patterns:
            for match in re.finditer(pattern, evidence, re.IGNORECASE):
                if len(match.groups()) == 3:
                    concept, column, value = match.groups()
                elif len(match.groups()) == 2:
                    column, value = match.groups()
                    concept = None
                else:
                    continue

                column = column.strip().strip('`')
                value = value.strip()

                # 检查这个条件是否在 SQL 的 WHERE 子句中
                where_body = self._where_body(sql)

                # 检查是否包含这个条件（灵活匹配）
                condition_found = False
                for col_form in [column, f'"{column}"', f'`{column}`']:
                    for val_form in [value, value.lower(), value.upper(), value.title()]:
                        if f"{col_form} = '{val_form}'" in sql or \
                           f"{col_form}='{val_form}'" in sql or \
                           f"{col_form} = \"{val_form}\"" in sql:
                            condition_found = True
                            break
                    if condition_found:
                        break

                if not condition_found:
                    # 提议添加这个条件
                    if where_body:
                        # 已有 WHERE，添加 AND 条件
                        new_where = f"{where_body} AND `{column}` = '{value}'"
                        new_sql = sql.replace(f"WHERE {where_body}", f"WHERE {new_where}")
                    else:
                        # 没有 WHERE，添加一个
                        # 在 FROM ... 后插入
                        from_match = re.search(r'(?is)\bfrom\b\s+\S+', sql)
                        if from_match:
                            insert_pos = from_match.end()
                            new_sql = sql[:insert_pos] + f" WHERE `{column}` = '{value}'" + sql[insert_pos:]
                        else:
                            continue

                    desc = f"add condition '{column}={value}' from evidence"
                    if concept:
                        desc += f" ('{concept}' refers to this)"
                    out.append(Candidate(new_sql, self.axis, desc))

        # ===== 3. 检查 Evidence 中定义的计算公式 =====
        # Pattern: "Rate = A / B"
        # Pattern: "percentage = (A / B) * 100"
        formula_pattern = r'(\w+)\s*=\s*([^.;]+(?:\([^)]+\))?[^.;]*)'

        # 检查是否是计算公式（包含运算符）
        for match in re.finditer(formula_pattern, evidence):
            lhs, rhs = match.groups()
            lhs = lhs.strip()
            rhs = rhs.strip()

            # 只处理包含运算符的公式
            if not any(op in rhs for op in ['/', '*', '+', '-', '(']):
                continue

            # 检查公式是否在 SQL 中实现
            # 提取公式中的列名
            formula_columns = re.findall(r'`([^`]+)`', rhs)

            if not formula_columns:
                # 如果没有 backticks，尝试提取单词
                formula_columns = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', rhs)

            # 检查这些列是否在 SELECT 中被使用
            select_body = self._select_body(sql)

            # 检查是否有算术表达式
            has_arithmetic = any(op in select_body for op in ['/', '*', '+', '-'])

            if formula_columns and not has_arithmetic:
                # SQL 没有实现公式，可能直接用了预计算的列
                # 提议实现公式

                # 构建公式（使用 backticks）
                formula_expr = rhs
                for col in formula_columns:
                    formula_expr = formula_expr.replace(col, f'`{col}`')

                # 替换 SELECT 中的第一个列
                select_match = re.search(r'(?is)^(select\s+)([^,\s]+)(.*?)(\s+from\b)', sql)
                if select_match:
                    prefix, first_col, rest, from_clause = select_match.groups()
                    new_sql = f"{prefix}{formula_expr}{rest}{from_clause}" + sql[select_match.end():]
                    out.append(Candidate(
                        new_sql, self.axis,
                        f"implement formula '{lhs} = {rhs}' from evidence"
                    ))

        # ===== 4. 检查 * 100 的百分比计算 =====
        # 如果 Evidence 提到 percentage/% 且包含 * 100 或 100
        has_percentage = bool(re.search(r'percent|%|\*\s*100|×\s*100|x\s*100', evidence, re.I))

        if has_percentage:
            has_100_in_sql = bool(re.search(r'\*\s*100|\*100', sql))

            if not has_100_in_sql:
                # 提议添加 * 100
                # 查找除法表达式
                select_body = self._select_body(sql)
                division_match = re.search(r'([^,]+/[^,]+)', select_body)

                if division_match:
                    division_expr = division_match.group(1).strip()
                    new_expr = f"({division_expr}) * 100"
                    new_sql = sql.replace(division_expr, new_expr, 1)
                    out.append(Candidate(
                        new_sql, self.axis,
                        "multiply by 100 for percentage (from evidence)"
                    ))

        # ===== 5. 检测使用预计算列 vs 应该计算公式 =====
        # Case 8: SQL使用 "Percent (%) Eligible Free" 列，但Evidence说要计算公式
        # 策略: 如果Evidence有公式，但WHERE/SELECT用了疑似预计算的列名
        if '=' in evidence and ('/' in evidence or '*' in evidence):
            # 查找Evidence中定义的列名 (左侧)
            formula_matches = re.findall(r'([\w\s]+)\s*=\s*`([^`]+)`\s*/\s*`([^`]+)`', evidence)

            for match in formula_matches:
                concept, numerator, denominator = match
                concept = concept.strip()

                # 检查SQL中是否直接使用了包含这个concept的预计算列
                # 比如 "Percent (%) Eligible Free (K-12)" 包含 "Percent"、"Free"等
                concept_words = concept.lower().split()

                # 查找WHERE和SELECT中的列
                for col_match in re.finditer(r'["\']([^"\']+)["\']|\b`([^`]+)`', sql):
                    col_name = col_match.group(1) or col_match.group(2)
                    if not col_name:
                        continue

                    col_lower = col_name.lower()

                    # 检查这个列名是否包含concept的词，且看起来是预计算的结果
                    if any(word in col_lower for word in concept_words if len(word) > 3):
                        # 可能是预计算列，建议用公式替换
                        # 构建公式
                        if numerator in ctx.columns or denominator in ctx.columns:
                            formula = f"CAST(`{numerator}` AS REAL) / `{denominator}`"

                            # 替换这个列引用
                            new_sql = sql.replace(f'"{col_name}"', formula)
                            new_sql = new_sql.replace(f'`{col_name}`', formula)
                            new_sql = new_sql.replace(f"'{col_name}'", formula)

                            if new_sql != sql:
                                out.append(Candidate(
                                    new_sql, self.axis,
                                    f"use formula '{numerator}/{denominator}' instead of precomputed column '{col_name[:30]}'"
                                ))

        return out[:8]  # 增加候选数量限制
