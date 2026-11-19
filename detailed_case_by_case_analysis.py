#!/usr/bin/env python3
"""
逐案例深度SQL错误分析 - 检查实际数据找出真正问题
"""

import sqlite3
import json
from pathlib import Path

class CaseByCase:
    """逐个案例深入分析SQL错误的真正原因"""

    def __init__(self):
        self.db_path = Path('/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/phase2_final/dev/dev_databases/california_schools/california_schools.sqlite')
        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()

    def analyze_case_0(self):
        """QID 0: 最高的K-12免费餐比率"""
        print("\n" + "="*80)
        print("QID 0: What is the highest eligible free rate for K-12 students in Alameda County?")
        print("问题: Pred SQL乘了100，把比率变成了百分比")

        gold_sql = "SELECT `Free Meal Count (K-12)` / `Enrollment (K-12)` FROM frpm WHERE `County Name` = 'Alameda' ORDER BY (CAST(`Free Meal Count (K-12)` AS REAL) / `Enrollment (K-12)`) DESC LIMIT 1"
        pred_sql = 'SELECT MAX(CAST("Free Meal Count (K-12)" AS REAL) * 100.0 / "Enrollment (K-12)") FROM frpm WHERE "County Name" = \'Alameda\''

        self.cursor.execute(gold_sql)
        gold_result = self.cursor.fetchall()
        print(f"Gold结果: {gold_result}")  # [(1.0,)]

        self.cursor.execute(pred_sql)
        pred_result = self.cursor.fetchall()
        print(f"Pred结果: {pred_result}")  # [(100.0,)]

        print("\n错误原因: Pred SQL错误地乘了100，将比率转换成百分比")
        print("修复建议: 去掉 * 100.0")

        return {
            'qid': '0',
            'error': '单位转换错误 - 不应该乘100',
            'category': 'CALCULATION_ERROR'
        }

    def analyze_case_1(self):
        """QID 1: continuation schools的免费餐比率"""
        print("\n" + "="*80)
        print("QID 1: lowest three eligible free rates for students aged 5-17 in continuation schools")

        # 先检查frpm表的列名
        self.cursor.execute("PRAGMA table_info(frpm)")
        columns = self.cursor.fetchall()
        print("\nfrpm表的列名:")
        for col in columns:
            if 'school' in col[1].lower() or 'type' in col[1].lower() or 'educational' in col[1].lower():
                print(f"  {col[1]}")

        # 检查有哪些学校类型
        self.cursor.execute("SELECT DISTINCT `Educational Option Type` FROM frpm WHERE `Educational Option Type` IS NOT NULL LIMIT 10")
        types = self.cursor.fetchall()
        print("\nEducational Option Type的值:")
        for t in types:
            print(f"  {t[0]}")

        # 检查是否有School Type列
        try:
            self.cursor.execute('SELECT DISTINCT "School Type" FROM frpm LIMIT 5')
            school_types = self.cursor.fetchall()
            print("\nSchool Type的值:")
            for t in school_types:
                print(f"  {t[0]}")
        except:
            print("\nSchool Type列不存在")

        # 执行Gold SQL
        gold_sql = "SELECT `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` FROM frpm WHERE `Educational Option Type` = 'Continuation School' AND `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` IS NOT NULL ORDER BY `Free Meal Count (Ages 5-17)` / `Enrollment (Ages 5-17)` ASC LIMIT 3"
        self.cursor.execute(gold_sql)
        gold_result = self.cursor.fetchall()
        print(f"\nGold结果: {gold_result}")

        # 执行Pred SQL会返回空
        pred_sql = 'SELECT CAST("Free Meal Count (Ages 5-17)" AS REAL) / "Enrollment (Ages 5-17)" FROM frpm WHERE "School Type" = \'Continuation Schools\' ORDER BY CAST("Free Meal Count (Ages 5-17)" AS REAL) / "Enrollment (Ages 5-17)" ASC LIMIT 3'

        print("\n错误原因:")
        print("1. 使用了错误的列名: 'School Type' vs 'Educational Option Type'")
        print("2. 使用了错误的值: 'Continuation Schools' (复数) vs 'Continuation School' (单数)")

        return {
            'qid': '1',
            'error': '列名错误和值不匹配',
            'category': 'COLUMN_VALUE_ERROR'
        }

    def analyze_case_15(self):
        """QID 15: 最高平均阅读分数的活跃学区"""
        print("\n" + "="*80)
        print("QID 15: Which active district has the highest average score in Reading?")

        # Gold SQL - 找每个学校的分数，然后取最高的那个学校所在的学区
        gold_sql = "SELECT T1.District FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T1.StatusType = 'Active' ORDER BY T2.AvgScrRead DESC LIMIT 1"

        # Pred SQL - 对每个学区的所有学校求平均
        pred_sql = 'SELECT T1.District FROM schools AS T1 INNER JOIN satscores AS T2 ON T1."CDSCode" = T2.cds WHERE T1.StatusType = \'Active\' GROUP BY T1.District ORDER BY AVG(T2.AvgScrRead) DESC LIMIT 1'

        self.cursor.execute(gold_sql)
        gold_result = self.cursor.fetchall()
        print(f"Gold结果 (找分数最高的单个学校): {gold_result}")

        self.cursor.execute(pred_sql)
        pred_result = self.cursor.fetchall()
        print(f"Pred结果 (找平均分最高的学区): {pred_result}")

        print("\n问题分析:")
        print("Gold SQL: 找拥有最高分学校的学区（单个学校的最高分）")
        print("Pred SQL: 找平均分最高的学区（学区内所有学校的平均）")
        print("\n错误原因: 理解偏差 - 不应该GROUP BY和AVG，应该直接找最高分")

        return {
            'qid': '15',
            'error': '错误使用了GROUP BY和AVG聚合',
            'category': 'AGGREGATION_ERROR'
        }

    def analyze_case_16(self):
        """QID 16: merged Alameda的学校数量"""
        print("\n" + "="*80)
        print("QID 16: How many schools in merged Alameda have number of test takers less than 100?")

        # 问题描述有歧义："merged Alameda"
        # Gold SQL使用: StatusType = 'Merged' AND County = 'Lake' (!!!注意是Lake不是Alameda)
        # Pred SQL使用: County = 'Alameda'

        gold_sql = "SELECT COUNT(T1.CDSCode) FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T1.StatusType = 'Merged' AND T2.NumTstTakr < 100 AND T1.County = 'Lake'"
        pred_sql = "SELECT COUNT(T1.CDSCode) FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T1.County = 'Alameda' AND T2.NumTstTakr < 100"

        print("\nGold SQL条件: StatusType = 'Merged' AND County = 'Lake'")
        print("Pred SQL条件: County = 'Alameda'")

        self.cursor.execute(gold_sql)
        gold_result = self.cursor.fetchall()
        print(f"Gold结果: {gold_result}")

        self.cursor.execute(pred_sql)
        pred_result = self.cursor.fetchall()
        print(f"Pred结果: {pred_result}")

        print("\n重大问题: Gold SQL用的是Lake县，而问题说的是Alameda！")
        print("这可能是Gold SQL本身的错误，或者问题描述有误")

        return {
            'qid': '16',
            'error': 'Gold SQL可能有错 - 县名不一致',
            'category': 'GOLD_SQL_ERROR'
        }

    def analyze_case_22(self):
        """QID 22: Contra Costa县测试人数最多的学校"""
        print("\n" + "="*80)
        print("QID 22: Which school in Contra Costa has the highest number of test takers?")

        # 检查satscores表的列
        self.cursor.execute("PRAGMA table_info(satscores)")
        columns = self.cursor.fetchall()
        print("\nsatscores表的列:")
        for col in columns:
            if 'name' in col[1].lower() or 'county' in col[1].lower():
                print(f"  {col[1]}")

        # Gold SQL直接在satscores表中查询
        gold_sql = "SELECT sname FROM satscores WHERE cname = 'Contra Costa' AND sname IS NOT NULL ORDER BY NumTstTakr DESC LIMIT 1"

        try:
            self.cursor.execute(gold_sql)
            gold_result = self.cursor.fetchall()
            print(f"\nGold结果: {gold_result}")
        except Exception as e:
            print(f"\nGold SQL执行错误: {e}")

        # Pred SQL通过JOIN查询
        pred_sql = "SELECT T1.School FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds WHERE T1.County = 'Contra Costa' ORDER BY T2.NumTstTakr DESC LIMIT 1"

        self.cursor.execute(pred_sql)
        pred_result = self.cursor.fetchall()
        print(f"Pred结果: {pred_result}")

        # 检查satscores表是否有直接的学校名和县名
        self.cursor.execute("SELECT * FROM satscores LIMIT 1")
        sample = self.cursor.fetchone()
        print(f"\nsatscores表样本: {sample}")

        print("\n错误原因: satscores表有自己的sname和cname列，不需要JOIN")
        print("Pred SQL的JOIN可能导致某些学校被过滤掉")

        return {
            'qid': '22',
            'error': '不必要的JOIN导致数据丢失',
            'category': 'JOIN_ERROR'
        }

    def analyze_all(self):
        """分析所有案例"""
        results = []
        results.append(self.analyze_case_0())
        results.append(self.analyze_case_1())
        results.append(self.analyze_case_15())
        results.append(self.analyze_case_16())
        results.append(self.analyze_case_22())

        # 总结
        print("\n" + "="*80)
        print("错误类型总结:")
        error_types = {}
        for r in results:
            cat = r['category']
            if cat not in error_types:
                error_types[cat] = []
            error_types[cat].append(r['qid'])

        for cat, qids in error_types.items():
            print(f"  {cat}: QIDs {', '.join(qids)}")

        return results


if __name__ == "__main__":
    analyzer = CaseByCase()
    results = analyzer.analyze_all()

    # 保存结果
    with open('/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/case_by_case_analysis.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n分析完成，结果已保存")