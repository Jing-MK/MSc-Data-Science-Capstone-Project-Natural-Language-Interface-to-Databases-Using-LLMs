# DeepEye-SQL BIRD Benchmark 评测指南

## 环境配置

已完成以下环境设置：
- ✅ Python 3.11 虚拟环境（venv_new）
- ✅ 所有必需依赖已安装
- ✅ Qwen3.7-plus API 配置已设置
- ✅ 数据集预处理已完成（workspace/dataset/bird/dev.snapshot）

## 数据集信息

- **数据集**: BIRD dev
- **题目数量**: 1534 题
- **数据库数量**: 11 个数据库
- **数据位置**: `/Users/jing/Desktop/capstone project/Capstone_DIN/DeepEye-SQL/dev/`

## 配置文件

### 完整评测配置
- **配置文件**: `config/config-bird-qwen3.7-plus.toml`
- **模型**: Qwen3.7-plus
- **API地址**: https://ws-eaupirv72jshfzn3.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
- **参数**: temperature=0, max_tokens=2000, enable_thinking=false

## 运行评测

### 方式1: 完整自动运行（推荐）

```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/DeepEye-SQL"
./run_full_evaluation.sh 2>&1 | tee evaluation_log.txt
```

### 方式2: 分步运行

```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/DeepEye-SQL"
source venv_new/bin/activate
export CONFIG_PATH="config/config-bird-qwen3.7-plus.toml"

# 步骤1: 创建向量数据库（如果还没有创建）
python3 runner/create_vector_db_parallel.py

# 步骤2: 值检索
python3 runner/run_value_retrieval.py

# 步骤3: Schema链接
python3 runner/run_schema_linking.py

# 步骤4: SQL生成
python3 runner/run_sql_generation.py

# 步骤5: SQL修订
python3 runner/run_sql_revision.py

# 步骤6: SQL选择
python3 runner/run_sql_selection.py

# 步骤7: 转换结果
python3 runner/convert_snapshot_to_sql.py --snapshot_path workspace/sql_selection/bird/dev.snapshot

# 步骤8: 评测
python3 runner/evaluation.py --snapshot_path workspace/sql_selection/bird/dev.snapshot --dataset_type bird
```

## 评测流程

完整的评测流程包括以下阶段：

1. **向量数据库创建** (create_vector_db_parallel.py)
   - 为所有数据库列创建向量索引
   - 用于后续的值检索

2. **值检索** (run_value_retrieval.py)
   - 从数据库中检索相关的值
   - 使用向量相似度搜索

3. **Schema链接** (run_schema_linking.py)
   - 直接链接（Direct Linking）
   - 反向链接（Reversed Linking）
   - 值链接（Value Linking）

4. **SQL生成** (run_sql_generation.py)
   - 使用多种生成策略：
     - DC Generator
     - Skeleton Generator
     - ICL Generator

5. **SQL修订** (run_sql_revision.py)
   - 语法检查
   - 执行检查
   - 结果检查

6. **SQL选择** (run_sql_selection.py)
   - 从候选SQL中选择最佳结果
   - 基于执行结果的比较

7. **结果转换和评测**
   - 转换为标准格式
   - 计算准确率
   - 生成错题分析

## 输出文件

评测完成后，结果保存在以下位置：

- **最终快照**: `workspace/sql_selection/bird/dev.snapshot`
- **SQL结果**: `workspace/sql_selection/bird/dev_pred.sql` （由convert_snapshot_to_sql.py生成）
- **评测报告**: 终端输出中包含准确率统计

## 查看结果

### 查看准确率

评测脚本会在最后输出类似以下的结果：

```
Execution Accuracy: XX.XX%
Total Questions: 1534
Correct: XXX
Incorrect: XXX
```

### 查看错题

可以通过分析snapshot文件查看详细的错题信息：

```python
import json

# 读取snapshot
with open('workspace/sql_selection/bird/dev.snapshot', 'r') as f:
    data = json.load(f)

# 查看每道题的结果
for item in data:
    question_id = item['question_id']
    question = item['question']
    gold_sql = item['gold_sql']
    predicted_sql = item.get('final_selected_sql', '')

    # 可以添加更多分析逻辑
```

### 生成错题报告脚本

```python
import json
from pathlib import Path

# 读取快照
snapshot_path = Path('workspace/sql_selection/bird/dev.snapshot')
with open(snapshot_path, 'r') as f:
    results = json.load(f)

# 分析错题
errors = []
for item in results:
    # 这里需要根据实际的数据结构来判断是否正确
    # 通常需要执行SQL并比较结果
    pass

# 生成报告
with open('error_analysis.md', 'w') as f:
    f.write('# BIRD Benchmark 错题分析\\n\\n')
    f.write(f'总题数: {len(results)}\\n')
    f.write(f'错题数: {len(errors)}\\n')
    # 添加更多分析内容
```

## 预计运行时间

根据1534题的规模和API调用次数，预计总运行时间：

- 向量数据库创建: 30-60分钟
- 值检索: 1-2小时
- Schema链接: 1-2小时
- SQL生成: 3-5小时
- SQL修订: 2-3小时
- SQL选择: 1-2小时

**总计: 约8-14小时**

注意：实际时间取决于API响应速度和网络状况。

## 故障排除

### 如果某个阶段失败

DeepEye-SQL使用checkpoint机制，可以从失败的地方继续：

```bash
# 例如，如果SQL生成阶段失败，可以直接重新运行
python3 runner/run_sql_generation.py
```

系统会自动从已完成的样本继续处理。

### 查看日志

每个阶段都会输出详细日志，可以使用tee命令保存：

```bash
python3 runner/run_sql_generation.py 2>&1 | tee sql_generation.log
```

## 联系信息

如有问题，请参考：
- DeepEye-SQL GitHub: https://github.com/HKUSTDial/DeepEye-SQL
- 论文: https://arxiv.org/abs/2510.17586
