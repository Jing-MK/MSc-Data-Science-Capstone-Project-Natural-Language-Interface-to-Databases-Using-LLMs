"""Question Entity Agent - 检查 SQL 中的值是否与 Question 中的实体匹配

很多错误是因为 SQL 使用了错误的 WHERE 值，这些值没有在 Question 中出现。
例如：Question 说 "Alameda" 但 SQL 用了 "Lake"。

这个 Agent 检查：
1. SQL WHERE 子句中的值是否在 Question 中
2. 如果不在，尝试用 Question 中的实体替换
"""
import re
from agents.base import Agent
from engine.types import Candidate


class QuestionEntityAgent(Agent):
    axis = "question_entity"

    def _extract_entities(self, text):
        """提取文本中的命名实体（简单版本）"""
        entities = []

        # 1. 提取引号中的内容
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", text)
        entities.extend(quoted)

        # 2. 提取首字母大写的词组（2-4 个词）
        capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b', text)
        entities.extend(capitalized)

        # 3. 提取数字
        numbers = re.findall(r'\b\d+\b', text)
        entities.extend(numbers)

        # 4. 提取特殊关键词后的内容
        # "in X", "from X", "at X", "named X"
        for pattern in [
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bfrom\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bnamed\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bcalled\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        # 去重并返回
        return list(set(e.strip() for e in entities if len(e.strip()) > 1))

    def _extract_where_values(self, sql):
        """提取 SQL WHERE 子句中的所有字符串值"""
        where_body = self._where_body(sql)
        if not where_body:
            return []

        # 提取所有单引号和双引号中的值
        values = []
        values.extend(re.findall(r"'([^']+)'", where_body))
        values.extend(re.findall(r'"([^"]+)"', where_body))

        return [v.strip() for v in values]

    def _get_column_for_value(self, sql, value):
        """找出这个值对应的列名"""
        where_body = self._where_body(sql)
        if not where_body:
            return None

        # 查找 column = 'value' 或 column='value' 模式
        patterns = [
            rf'([`"\w\s.]+)\s*=\s*[\'"]{re.escape(value)}[\'"]',
            rf'([`"\w\s.]+)=[\'"]{re.escape(value)}[\'"]',
        ]

        for pattern in patterns:
            match = re.search(pattern, where_body, re.IGNORECASE)
            if match:
                col = match.group(1).strip()
                # 去掉表前缀和引号
                col = re.sub(r'^\w+\.', '', col)
                col = col.strip('`"')
                return col

        return None

    def _are_similar_type(self, val1, val2, ctx):
        """判断两个值是否是相似类型（都是地名、都是状态等）"""
        # 如果值相似度很高，认为是同类型
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, val1.lower(), val2.lower()).ratio()
        if ratio > 0.6:
            return True

        # 如果它们对应同一个列，认为是同类型
        # （这需要查询数据库，简化版本先跳过）

        # 如果都是首字母大写的词组，认为可能是同类型（地名、人名等）
        if val1[0].isupper() and val2[0].isupper():
            return True

        return False

    def enumerate(self, sql, ctx):
        if not ctx.question:
            return []

        out = []

        # 提取 Question 中的实体
        question_entities = self._extract_entities(ctx.question)

        # 提取 SQL WHERE 子句中的值
        sql_values = self._extract_where_values(sql)

        # 对于每个 SQL 值
        for sql_val in sql_values:
            # 检查是否在 Question 中
            # 灵活匹配：忽略大小写、部分匹配
            found_in_question = False

            for entity in question_entities:
                # 完全匹配（忽略大小写）
                if sql_val.lower() == entity.lower():
                    found_in_question = True
                    break
                # 部分匹配
                if sql_val.lower() in entity.lower() or entity.lower() in sql_val.lower():
                    found_in_question = True
                    break

            if not found_in_question:
                # 这个值不在 Question 中，可能是错误的
                # 尝试用 Question 中的实体替换

                # 找出这个值对应的列
                column = self._get_column_for_value(sql, sql_val)

                if not column:
                    continue

                # 对于每个 Question 实体，如果类型相似，提议替换
                for entity in question_entities:
                    if entity.lower() == sql_val.lower():
                        continue

                    # 检查是否是相似类型
                    if self._are_similar_type(sql_val, entity, ctx):
                        # 提议替换
                        # 保持原始 SQL 中值的引号风格
                        if f"'{sql_val}'" in sql:
                            new_sql = sql.replace(f"'{sql_val}'", f"'{entity}'")
                        elif f'"{sql_val}"' in sql:
                            new_sql = sql.replace(f'"{sql_val}"', f'"{entity}"')
                        else:
                            continue

                        if new_sql != sql:
                            out.append(Candidate(
                                new_sql, self.axis,
                                f"replace '{sql_val}' with '{entity}' from question"
                            ))

        return out[:5]  # 限制候选数量
