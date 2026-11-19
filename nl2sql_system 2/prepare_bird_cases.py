"""
Prepare BIRD dev cases for Phase 2 evaluation.

This script combines:
- dev.json (questions, evidence, db_id)
- predict_dev_qwen_plus.json (predicted SQL)
- dev_gold.sql (gold SQL)

Output: bird_cases.json for evaluation
"""
import json
import sys

def load_gold_sql(gold_path):
    """Load gold SQL from tab-separated file."""
    gold_sqls = []
    with open(gold_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                sql = parts[0]
                db_id = parts[1]
                gold_sqls.append({'sql': sql, 'db_id': db_id})
            else:
                gold_sqls.append({'sql': line, 'db_id': 'unknown'})
    return gold_sqls

def main():
    # Paths
    dev_json_path = "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/phase2_final/dev/dev.json"
    predict_path = "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/phase2_final/predict_dev_qwen_plus.json"
    gold_path = "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/dev_gold.sql"

    # Load data
    print("Loading BIRD dev data...")
    with open(dev_json_path, 'r', encoding='utf-8') as f:
        dev_data = json.load(f)
    print(f"✓ Loaded {len(dev_data)} questions from dev.json")

    print("Loading predictions...")
    with open(predict_path, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    print(f"✓ Loaded {len(predictions)} predictions")

    print("Loading gold SQL...")
    gold_sqls = load_gold_sql(gold_path)
    print(f"✓ Loaded {len(gold_sqls)} gold SQLs")

    # Verify counts match
    if not (len(dev_data) == len(predictions) == len(gold_sqls)):
        print(f"⚠️  Warning: Counts don't match!")
        print(f"   dev.json: {len(dev_data)}")
        print(f"   predictions: {len(predictions)}")
        print(f"   gold SQL: {len(gold_sqls)}")
        min_count = min(len(dev_data), len(predictions), len(gold_sqls))
        print(f"   Using first {min_count} cases")
    else:
        min_count = len(dev_data)
        print(f"✓ All counts match: {min_count} cases")

    # Combine data
    print("\nPreparing cases...")
    cases = []
    for i in range(min_count):
        # Parse prediction (format: "SQL\t----- bird -----\tdb_id")
        pred_value = predictions[str(i)]
        if isinstance(pred_value, str):
            pred_parts = pred_value.split('\t')
            predicted_sql = pred_parts[0] if pred_parts else pred_value
        else:
            predicted_sql = str(pred_value)

        case = {
            'db_id': dev_data[i]['db_id'],
            'question': dev_data[i]['question'],
            'evidence': dev_data[i].get('evidence', ''),
            'predicted_sql': predicted_sql,
            'gold_sql': gold_sqls[i]['sql']
        }

        # Verify db_id matches
        if gold_sqls[i]['db_id'] != 'unknown' and case['db_id'] != gold_sqls[i]['db_id']:
            print(f"⚠️  Warning: db_id mismatch at index {i}")
            print(f"   dev.json: {case['db_id']}")
            print(f"   gold SQL: {gold_sqls[i]['db_id']}")

        cases.append(case)

    # Save
    output_path = "bird_cases.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(cases)} cases to {output_path}")

    # Show sample
    print("\n📋 Sample case:")
    sample = cases[0]
    print(f"   DB: {sample['db_id']}")
    print(f"   Question: {sample['question'][:80]}...")
    print(f"   Evidence: {sample['evidence'][:80] if sample['evidence'] else '(none)'}...")
    print(f"   Predicted SQL: {sample['predicted_sql'][:80]}...")
    print(f"   Gold SQL: {sample['gold_sql'][:80]}...")

    # Statistics
    print("\n📊 Statistics:")
    db_counts = {}
    for case in cases:
        db_id = case['db_id']
        db_counts[db_id] = db_counts.get(db_id, 0) + 1

    print(f"   Total databases: {len(db_counts)}")
    print(f"   Top 5 databases:")
    for db, count in sorted(db_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"     - {db}: {count} questions")

    has_evidence = sum(1 for c in cases if c['evidence'])
    print(f"   Cases with evidence: {has_evidence}/{len(cases)} ({has_evidence/len(cases)*100:.1f}%)")

if __name__ == '__main__':
    main()
