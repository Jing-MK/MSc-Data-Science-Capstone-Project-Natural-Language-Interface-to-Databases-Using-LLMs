import json

with open('error_analysis.json', 'r') as f:
    data = json.load(f)

print('文件结构:')
print('- total_errors:', data['total_errors'])
print('- error_type_counts: 包含', len(data['error_type_counts']), '种错误类型')
print('- error_categories: 包含分类后的具体案例')
print('\n前5种最常见错误:')
for i, (k, v) in enumerate(list(data['error_type_counts'].items())[:5], 1):
    print(f'{i}. {k}: {v}个案例')

print('\n每种错误类型都包含了具体的错误案例，包括:')
first_type = list(data['error_categories'].keys())[0]
if first_type in data['error_categories'] and data['error_categories'][first_type]:
    example = data['error_categories'][first_type][0]
    print('- qid: 问题ID')
    print('- question: 原始问题')
    print('- gold_sql: 正确SQL')
    print('- pred_sql: 预测SQL')
    print('- difficulty: 难度等级')
    print('- db_id: 数据库ID')