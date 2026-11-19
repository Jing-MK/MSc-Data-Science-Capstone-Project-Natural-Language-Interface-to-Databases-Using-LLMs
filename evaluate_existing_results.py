#!/usr/bin/env python3
"""
评测已有的预测结果文件
直接评测 results/bird-dev/qwen3-coder-30b-a3b.json
"""

import json
import sqlite3
from pathlib import Path
from collections import defaultdict

def load_gold_data(json_path):
    """加载标准答案数据"""
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data

def load_predictions(pred_path):
    """加载预测结果"""
    with open(pred_path, 'r') as f:
        predictions = json.load(f)
    return predictions

def execute_sql(database_path, sql):
    """执行SQL并返回结果"""
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result, None
    except Exception as e:
        return None, str(e)

def compare_results(result1, result2):
    """比较两个SQL执行结果是否相同"""
    if result1 is None or result2 is None:
        return False

    try:
        # 转换为集合进行比较（忽略顺序）
        set1 = {tuple(row) for row in result1}
        set2 = {tuple(row) for row in result2}
        return set1 == set2
    except:
        return False

def evaluate():
    """执行评测"""
    print("=" * 60)
    print("BIRD Dev Benchmark 评测")
    print("模型: Qwen3-Coder-30B-A3B (官方结果)")
    print("=" * 60)
    print()

    # 加载数据
    gold_data = load_gold_data('dev/dev.json')
    predictions = load_predictions('results/bird-dev/qwen3-coder-30b-a3b.json')

    print(f"标准答案数量: {len(gold_data)}")
    print(f"预测结果数量: {len(predictions)}")
    print()

    # 统计
    total = 0
    correct = 0
    errors = []
    difficulty_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
    database_stats = defaultdict(lambda: {'total': 0, 'correct': 0})

    # 逐题评测
    for i, item in enumerate(gold_data):
        question_id = item.get('question_id')
        question = item.get('question')
        gold_sql = item.get('SQL')
        difficulty = item.get('difficulty', 'unknown')
        db_id = item.get('db_id')
        evidence = item.get('evidence', '')

        # 获取预测SQL
        pred_sql = predictions.get(str(question_id), '')

        # 数据库路径
        database_path = f'dev/dev_databases/{db_id}/{db_id}.sqlite'

        total += 1
        difficulty_stats[difficulty]['total'] += 1
        database_stats[db_id]['total'] += 1

        # 执行并比较
        is_correct = False
        error_msg = ""

        if not pred_sql:
            error_msg = "缺少预测SQL"
        else:
            gold_result, gold_error = execute_sql(database_path, gold_sql)
            pred_result, pred_error = execute_sql(database_path, pred_sql)

            if gold_error:
                error_msg = f"标准SQL执行错误: {gold_error}"
            elif pred_error:
                error_msg = f"预测SQL执行错误: {pred_error}"
            elif compare_results(gold_result, pred_result):
                is_correct = True
            else:
                error_msg = "结果不匹配"

        if is_correct:
            correct += 1
            difficulty_stats[difficulty]['correct'] += 1
            database_stats[db_id]['correct'] += 1
        else:
            errors.append({
                'question_id': question_id,
                'database': db_id,
                'difficulty': difficulty,
                'question': question,
                'evidence': evidence,
                'gold_sql': gold_sql,
                'pred_sql': pred_sql,
                'error': error_msg
            })

        # 进度
        if (i + 1) % 100 == 0:
            print(f"进度: {i+1}/{total} ({(i+1)/total*100:.1f}%) - 当前准确率: {correct/(i+1)*100:.2f}%")

    # 输出结果
    print()
    print("=" * 60)
    print("评测结果")
    print("=" * 60)
    print(f"总题数: {total}")
    print(f"正确数: {correct}")
    print(f"错误数: {total - correct}")
    print(f"准确率: {correct/total*100:.2f}%")
    print("=" * 60)
    print()

    # 按难度统计
    print("按难度统计:")
    print("-" * 60)
    for difficulty in sorted(difficulty_stats.keys()):
        stats = difficulty_stats[difficulty]
        acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {difficulty:15s}: {stats['correct']:4d}/{stats['total']:4d} ({acc:6.2f}%)")
    print()

    # 按数据库统计
    print("按数据库统计:")
    print("-" * 60)
    for db_id in sorted(database_stats.keys(), key=lambda x: database_stats[x]['total'], reverse=True):
        stats = database_stats[db_id]
        acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"  {db_id:30s}: {stats['correct']:4d}/{stats['total']:4d} ({acc:6.2f}%)")
    print()

    # 保存错题
    print(f"保存错题到: error_analysis.json")
    with open('error_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    # 生成简要报告
    with open('evaluation_summary.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("BIRD Dev Benchmark 评测结果\n")
        f.write("模型: Qwen3-Coder-30B-A3B\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"总题数: {total}\n")
        f.write(f"正确数: {correct}\n")
        f.write(f"错误数: {total - correct}\n")
        f.write(f"准确率: {correct/total*100:.2f}%\n\n")

        f.write("按难度统计:\n")
        f.write("-" * 60 + "\n")
        for difficulty in sorted(difficulty_stats.keys()):
            stats = difficulty_stats[difficulty]
            acc = stats['correct'] / stats['total'] * 100 if stats['total'] > 0 else 0
            f.write(f"  {difficulty:15s}: {stats['correct']:4d}/{stats['total']:4d} ({acc:6.2f}%)\n")

        f.write("\n错题前10个:\n")
        f.write("-" * 60 + "\n")
        for i, error in enumerate(errors[:10], 1):
            f.write(f"\n{i}. ID={error['question_id']}, DB={error['database']}, Difficulty={error['difficulty']}\n")
            f.write(f"   问题: {error['question']}\n")
            f.write(f"   错误: {error['error']}\n")

    print("评测完成！结果已保存到 evaluation_summary.txt")

if __name__ == '__main__':
    evaluate()
