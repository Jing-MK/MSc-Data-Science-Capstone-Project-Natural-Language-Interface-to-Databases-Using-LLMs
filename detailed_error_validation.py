#!/usr/bin/env python3
"""
Phase 2 详细错误验证脚本
逐个验证每个错误案例，通过实际执行SQL来确定准确的错误原因
"""

import json
import sqlite3
import os
from typing import Dict, List, Tuple, Optional
import re
from pathlib import Path

class SQLErrorValidator:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.dev_db_path = self.base_path / "baselines/phase2_final/dev/dev_databases"
        self.connections = {}

    def get_db_connection(self, db_id: str) -> sqlite3.Connection:
        """获取或创建数据库连接"""
        if db_id not in self.connections:
            db_path = self.dev_db_path / f"{db_id}/{db_id}.sqlite"
            if not db_path.exists():
                print(f"警告: 数据库 {db_path} 不存在")
                return None
            self.connections[db_id] = sqlite3.connect(str(db_path))
        return self.connections[db_id]

    def execute_sql(self, conn: sqlite3.Connection, sql: str) -> Tuple[bool, Optional[List], Optional[str]]:
        """执行SQL并返回结果"""
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            return True, results, None
        except Exception as e:
            return False, None, str(e)

    def get_table_schema(self, conn: sqlite3.Connection) -> Dict:
        """获取数据库schema信息"""
        cursor = conn.cursor()

        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema[table_name] = [col[1] for col in columns]

        return schema

    def analyze_single_error(self, case: Dict) -> Dict:
        """详细分析单个错误案例"""
        qid = case['qid']
        question = case['question']
        evidence = case.get('evidence', '')
        gold_sql = case['gold_sql']
        pred_sql = case['pred_sql']
        db_id = case.get('db_id', 'unknown')

        print(f"\n{'='*80}")
        print(f"分析 QID: {qid}")
        print(f"问题: {question}")
        if evidence:
            print(f"证据: {evidence}")
        print(f"数据库: {db_id}")

        # 获取数据库连接
        conn = self.get_db_connection(db_id)
        if not conn:
            return {
                'qid': qid,
                'error_type': 'database_not_found',
                'details': f'数据库 {db_id} 未找到'
            }

        # 获取schema
        schema = self.get_table_schema(conn)
        print(f"\n数据库表: {list(schema.keys())}")

        # 执行Gold SQL
        print(f"\n执行 Gold SQL:")
        print(f"  {gold_sql[:200]}...")
        gold_success, gold_results, gold_error = self.execute_sql(conn, gold_sql)

        if not gold_success:
            print(f"  ❌ Gold SQL 执行失败: {gold_error}")
            error_type = 'gold_sql_error'
            details = f"Gold SQL本身有错误: {gold_error}"
        else:
            print(f"  ✓ Gold SQL 成功，返回 {len(gold_results)} 行")
            if gold_results and len(gold_results) <= 3:
                print(f"  结果: {gold_results}")

        # 执行Pred SQL
        print(f"\n执行 Pred SQL:")
        print(f"  {pred_sql[:200]}...")
        pred_success, pred_results, pred_error = self.execute_sql(conn, pred_sql)

        if not pred_success:
            print(f"  ❌ Pred SQL 执行失败: {pred_error}")
            error_type, details = self.classify_execution_error(pred_error, pred_sql, schema)
        else:
            print(f"  ✓ Pred SQL 成功，返回 {len(pred_results)} 行")
            if pred_results and len(pred_results) <= 3:
                print(f"  结果: {pred_results}")

            # 比较结果
            if gold_success:
                error_type, details = self.compare_results(
                    gold_results, pred_results, gold_sql, pred_sql, question, evidence
                )
            else:
                error_type = 'comparison_impossible'
                details = 'Gold SQL执行失败，无法比较结果'

        return {
            'qid': qid,
            'question': question,
            'evidence': evidence,
            'db_id': db_id,
            'gold_sql': gold_sql,
            'pred_sql': pred_sql,
            'error_type': error_type,
            'details': details,
            'gold_success': gold_success,
            'pred_success': pred_success,
            'gold_rows': len(gold_results) if gold_results else 0,
            'pred_rows': len(pred_results) if pred_results else 0
        }

    def classify_execution_error(self, error_msg: str, sql: str, schema: Dict) -> Tuple[str, str]:
        """分类执行错误"""
        error_lower = error_msg.lower()

        if 'no such column' in error_lower:
            # 提取错误的列名
            match = re.search(r'no such column: (\S+)', error_lower)
            if match:
                wrong_col = match.group(1)
                # 检查是否是引号问题
                if '"' in wrong_col or '`' in wrong_col:
                    return 'column_quote_error', f'列名引号错误: {wrong_col}'
                else:
                    return 'column_not_exist', f'列不存在: {wrong_col}'
            return 'column_error', error_msg

        elif 'no such table' in error_lower:
            match = re.search(r'no such table: (\S+)', error_lower)
            if match:
                wrong_table = match.group(1)
                return 'table_not_exist', f'表不存在: {wrong_table}'
            return 'table_error', error_msg

        elif 'ambiguous column' in error_lower:
            return 'ambiguous_column', '列名歧义，需要指定表别名'

        elif 'syntax error' in error_lower:
            return 'syntax_error', f'SQL语法错误: {error_msg}'

        else:
            return 'execution_error', error_msg

    def compare_results(self, gold_results: List, pred_results: List,
                        gold_sql: str, pred_sql: str, question: str, evidence: str) -> Tuple[str, str]:
        """比较查询结果"""
        # 完全相同
        if gold_results == pred_results:
            return 'identical_results', '结果完全相同（可能是评估脚本的问题）'

        # 行数不同
        if len(gold_results) != len(pred_results):
            if len(pred_results) == 0:
                return 'empty_result', f'预测SQL返回空结果，应返回{len(gold_results)}行'
            elif len(gold_results) == 0:
                return 'should_be_empty', f'预测SQL返回{len(pred_results)}行，但应该返回空结果'
            else:
                # 检查是否缺少DISTINCT
                if 'distinct' in gold_sql.lower() and 'distinct' not in pred_sql.lower():
                    return 'missing_distinct', f'缺少DISTINCT，返回{len(pred_results)}行而非{len(gold_results)}行'
                # 检查是否缺少LIMIT
                elif 'limit' in gold_sql.lower() and 'limit' not in pred_sql.lower():
                    return 'missing_limit', f'缺少LIMIT子句'
                else:
                    return 'row_count_mismatch', f'返回{len(pred_results)}行，应返回{len(gold_results)}行'

        # 行数相同但内容不同
        # 检查是否是排序问题
        gold_set = set(map(tuple, gold_results))
        pred_set = set(map(tuple, pred_results))

        if gold_set == pred_set:
            return 'order_difference', '结果集相同但顺序不同（可能缺少ORDER BY或排序方向错误）'

        # 检查是否是值的问题
        if len(gold_results) == 1 and len(pred_results) == 1:
            gold_val = gold_results[0]
            pred_val = pred_results[0]

            # 检查是否是计算问题
            if any(op in gold_sql for op in ['/', '*', '+', '-', 'CAST']):
                return 'calculation_error', f'计算结果错误: 预测{pred_val}, 应为{gold_val}'

            # 检查是否是聚合函数问题
            gold_aggs = re.findall(r'(COUNT|SUM|AVG|MAX|MIN)\s*\(', gold_sql.upper())
            pred_aggs = re.findall(r'(COUNT|SUM|AVG|MAX|MIN)\s*\(', pred_sql.upper())
            if gold_aggs != pred_aggs:
                return 'aggregation_error', f'聚合函数错误: 使用了{pred_aggs}而非{gold_aggs}'

        # 部分结果正确
        intersection = gold_set & pred_set
        if intersection:
            return 'partial_correct', f'部分结果正确: {len(intersection)}/{len(gold_set)}行匹配'

        return 'value_mismatch', '返回值完全不同'

    def close_all_connections(self):
        """关闭所有数据库连接"""
        for conn in self.connections.values():
            conn.close()

def validate_errors(input_file: str, output_file: str, limit: int = None):
    """验证所有错误案例"""
    # 加载错误案例
    with open(input_file, 'r') as f:
        data = json.load(f)

    error_cases = data['error_cases']
    if limit:
        error_cases = error_cases[:limit]

    # 创建验证器
    validator = SQLErrorValidator('/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2')

    # 验证每个案例
    validated_errors = []
    error_type_counts = {}

    for i, case in enumerate(error_cases):
        print(f"\n进度: {i+1}/{len(error_cases)}")
        result = validator.analyze_single_error(case)
        validated_errors.append(result)

        # 统计错误类型
        error_type = result['error_type']
        if error_type not in error_type_counts:
            error_type_counts[error_type] = 0
        error_type_counts[error_type] += 1

    # 关闭连接
    validator.close_all_connections()

    # 保存结果
    output_data = {
        'total_errors': len(validated_errors),
        'error_type_counts': dict(sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)),
        'validated_errors': validated_errors
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 打印总结
    print(f"\n{'='*80}")
    print(f"验证完成！共验证 {len(validated_errors)} 个错误案例")
    print(f"\n错误类型分布:")
    for error_type, count in sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / len(validated_errors)) * 100
        print(f"  {error_type}: {count} ({percentage:.1f}%)")

    print(f"\n详细结果已保存到: {output_file}")

if __name__ == "__main__":
    # 先验证前20个案例作为测试
    validate_errors(
        '/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/phase2_final/evaluation/eval_results.json',
        '/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/validated_errors.json',
        limit=20  # 先验证20个，确认脚本工作正常
    )