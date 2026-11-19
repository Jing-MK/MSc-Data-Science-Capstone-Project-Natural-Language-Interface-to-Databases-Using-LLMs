# Phase 2 系统完整运行指南

## 🎯 系统概览

Phase 2 实现了一个**两层架构的 Multi-Agent + HITL 纠错系统**：

- **Layer 1**: SQL Validation & Syntax Correction (自动化)
- **Layer 2**: Multi-Agent Logic Validation + HITL (智能自动化 + 人类监督)

---

## ✅ 系统已完成的功能

### 核心组件

1. **Multi-Agent System** (`agents/`)
   - ✅ Projection Agent (D2) - 列选择验证
   - ✅ Predicate Agent (D6) - 条件验证
   - ✅ Join Agent (D1) - 连接验证
   - ✅ Simple Clauses Agent (D3,D4,D7) - DISTINCT, 聚合, ORDER BY
   - ✅ Arithmetic Agent (D8) - 计算验证

2. **Execution Engine** (`engine/`)
   - ✅ Query execution with BIRD EX semantics
   - ✅ Schema introspection
   - ✅ Result clustering
   - ✅ Triage orchestrator (ABSTAIN/AUTOFIX/ASK)

3. **HITL Interface** (`hitl/`)
   - ✅ Multi-round correction loop
   - ✅ Constraint tracking
   - ✅ Deterministic stopping (4 rounds max)

4. **Evaluation** (`evaluation/`)
   - ✅ Three-arm comparison (no-correction / fix-always / ask-always / triage)
   - ✅ Oracle simulation
   - ✅ Metrics: N_fix, N_break, questions per query

---

## 🚀 运行方式

### 方式 1: Web 界面演示（推荐用于展示）✨

**当前状态**: Web 服务器已运行在后台

打开浏览器访问：
```
http://localhost:8501
```

**功能**:
- 📊 可视化表格展示
- 🖱️ 点击选择选项
- 📱 现代化 UI
- 🎨 实时系统状态

如果需要重启 Web 服务器：
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"
bash start_web_demo.sh
```

---

### 方式 2: 命令行交互演示

#### A. 交互式演示（需要用户输入）
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"
python3 demo_interactive.py
```

**流程**:
1. 系统显示问题和预测的 SQL
2. 检测到歧义时显示多个选项（实际数据表格）
3. 你输入选择（A/B/C）
4. 系统应用你的选择并显示最终结果

#### B. 自动演示（适合测试）
```bash
python3 demo_auto.py          # 自动选择第一个选项
python3 demo_presentation.py  # 详细的演示模式
python3 run_demo.py           # Oracle 模式（匹配 gold 结果）
```

---

### 方式 3: 评估系统（Three-Arm Evaluation）

#### A. 内置演示评估（4个案例）
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"
python3 -m evaluation.run_eval
```

**输出**（已验证）:
```
THREE-ARM EVALUATION  (4 cases)

no-correction
  EX: 50.0% -> 50.0%  (+0.0)
  N_fix=0  N_break=0  N_net=+0
  questions asked: 0  (0.00 per query)

fix-always
  EX: 50.0% -> 75.0%  (+25.0)
  N_fix=1  N_break=0  N_net=+1
  questions asked: 0  (0.00 per query)

ask-always
  EX: 50.0% -> 100.0%  (+50.0)
  N_fix=2  N_break=0  N_net=+2
  questions asked: 3  (0.75 per query)

triage (ours)
  EX: 50.0% -> 100.0%  (+50.0)
  N_fix=2  N_break=0  N_net=+2
  questions asked: 2  (0.50 per query)
```

**关键发现**:
- ✅ Triage 策略达到了和 ask-always 相同的准确率（100%）
- ✅ 但减少了 33% 的用户交互（2 vs 3 个问题）
- ✅ 没有破坏任何正确的查询（N_break=0）

#### B. BIRD 数据集评估

如果你有完整的 BIRD 数据集和预测结果：

```bash
# 1. 准备 cases.json
# 格式: [{"db_id": "...", "question": "...", "evidence": "...",
#         "predicted_sql": "...", "gold_sql": "..."}]

# 2. 运行评估
python3 -m evaluation.run_eval \
    --cases /path/to/cases.json \
    --dbroot "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/baselines/phase2_final/dev/dev_databases"
```

---

## 📊 评估结果解释

### Three-Arm Comparison

| Arm | 策略 | 目的 |
|-----|------|------|
| **no-correction** | 不做任何修改 | Baseline |
| **fix-always** | 检测到问题就自动修复 | 测试自动修复的上限 |
| **ask-always** | 检测到问题就询问用户 | 测试 HITL 的上限 |
| **triage (ours)** | 智能决策：高置信度自动修复，低置信度询问用户 | 我们的方法 |

### 指标说明

- **EX (Execution Accuracy)**: 执行准确率
- **N_fix**: 修复的错误数量（原本错误，修复后正确）
- **N_break**: 破坏的查询数量（原本正确，修复后错误）⚠️
- **N_net**: 净改进（N_fix - N_break）
- **questions per query**: 平均每个查询需要问用户几个问题

**理想的系统**:
- EX 提升越高越好
- N_fix 越多越好
- N_break = 0（不能破坏正确的查询）
- questions per query 越少越好（减少用户负担）

---

## 🎮 演示案例说明

系统包含 4 个内置演示案例：

### Case 1: 列名歧义
- **问题**: "names of schools in Alameda"
- **预测 SQL**: `SELECT "School Name" FROM schools WHERE County='Alameda'`
- **Gold SQL**: `SELECT School FROM schools WHERE County='Alameda'`
- **系统行为**:
  - 检测到两个候选列：`"School Name"` (完整名) vs `School` (简短名)
  - 展示两个选项的实际数据表
  - 用户选择正确的列

### Case 2: 大小写错误（自动修复）
- **问题**: "schools in Alameda (typo)"
- **预测 SQL**: `SELECT School FROM schools WHERE County='alameda'`
- **Gold SQL**: `SELECT School FROM schools WHERE County='Alameda'`
- **系统行为**:
  - 自动检测 `'alameda'` 应该是 `'Alameda'`
  - **自动修复**，无需用户交互
  - 置信度 = 0.99（非常确定）

### Case 3: 正确查询（不应修改）
- **问题**: "distinct counties"
- **预测 SQL**: `SELECT DISTINCT County FROM schools`
- **系统行为**:
  - 检测到查询已经正确
  - **ABSTAIN** - 不做任何修改
  - 保护正确的查询不被破坏

### Case 4: 另一个正确查询
- **问题**: "a correct query (must not be broken)"
- **系统行为**: ABSTAIN

---

## 🏗️ 系统架构

```
User Question + Predicted SQL
         │
         ▼
┌─────────────────────────────────────┐
│ Layer 1: SQL Validation (自动)      │
│ • SQL extraction                    │
│ • Syntax validation                 │
│ • Schema validation                 │
│ • Auto-correction                   │
└───────────┬─────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│ Layer 2: Multi-Agent + HITL         │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 5 Specialized Agents (Parallel) │ │
│ │ • Projection (列选择)            │ │
│ │ • Predicate (条件)              │ │
│ │ • Join (连接)                   │ │
│ │ • Simple Clauses (DISTINCT等)   │ │
│ │ • Arithmetic (计算)             │ │
│ └─────────────────────────────────┘ │
│            ↓                        │
│ ┌─────────────────────────────────┐ │
│ │ Execute & Cluster Results       │ │
│ └─────────────────────────────────┘ │
│            ↓                        │
│ ┌─────────────────────────────────┐ │
│ │ TRIAGE Decision                 │ │
│ │ • 1 cluster → ABSTAIN           │ │
│ │ • >1, objective → AUTOFIX       │ │
│ │ • >1, ambiguous → ASK user      │ │
│ └─────────────────────────────────┘ │
└───────────┬─────────────────────────┘
            │
            ▼
      Final SQL
```

---

## 🎯 核心创新点

### 1. Execution-Grounded Detection
- 不依赖模型预测正确性
- 基于**实际执行结果**的聚类
- 客观信号优先（如：只有一个结果非空）

### 2. Intelligent Triage
- **ABSTAIN**: 所有候选结果一致 → 不做修改
- **AUTOFIX**: 有客观信号（如非空结果唯一）→ 自动修复
- **ASK**: 多个合理结果，无客观信号 → 询问用户

### 3. Result-Based UI
- 不展示 SQL 代码给用户
- 展示**实际的数据表格**
- 用户只需选择"哪个答案是对的"

### 4. Multi-Round Correction
- 修复一个问题可能解决其他问题
- 每轮重新检测
- 最多 4 轮（覆盖 90% 的错误）

---

## 📈 预期性能

根据 Phase 2 设计文档的分析（477 个真实错误）：

### Layer 1 (Execution Errors: 47 个)
- **预期修复率**: 80-90%
- **方法**: 自动化（SQL 提取 + 语法修复 + Schema 匹配）

### Layer 2 (Wrong Results: 430 个)
- **自动修复** (置信度 ≥ 0.95): ~20 个
  - 大小写错误: 10/10
  - 值填充错误: 4/5
  - NULL 语法错误: 2/2

- **HITL 修复** (0.5 ≤ 置信度 < 0.95): 90-140 个
  - DISTINCT 错误: 25-35/48
  - 值选择错误: 20-30/56
  - JOIN 错误: 12-20/40
  - 聚合错误: 10-15/22
  - NULL 检查: 7-9/13

### 总体预期
- **Baseline**: 68.9%
- **+ Layer 1**: ~71-72%
- **+ Layer 2 (Oracle)**: **79-84%**
- **用户交互**: 每个查询 0.5-1.5 个问题（仅在需要时）

---

## 🛠️ 开发和调试

### 查看系统日志
系统的 `log` 参数可以打印详细的决策过程：

```python
from system import CorrectionSystem

sys = CorrectionSystem("demo.sqlite")
sys.run(
    question="...",
    predicted_sql="...",
    user=user_function,
    log=lambda m: print(f"[LOG] {m}")  # 打印所有决策
)
```

### 测试单个 Agent
```python
from agents.projection import ProjectionAgent
from engine.context import Context
from engine.schema import get_schema

schema = get_schema("demo.sqlite")
ctx = Context(schema, "SELECT School FROM schools")
agent = ProjectionAgent()

candidates = agent.enumerate(ctx)
print(f"Agent proposed {len(candidates)} alternatives")
```

---

## 📚 相关文档

- **架构设计**: `design/PHASE2_ARCHITECTURE.md`
- **完整设计**: `files/PHASE2_FINAL_DESIGN.md`
- **系统 README**: `README.md` 和 `README_ENHANCED.md`
- **演示说明**: `DEMO_INSTRUCTIONS.md`

---

## 🎓 论文贡献点

1. **Two-Layer Architecture**: 自动化 + 智能监督
2. **Multi-Agent System**: 专门化的错误检测
3. **Execution-Grounded**: 基于实际执行，不依赖 ML 判断
4. **Intelligent Triage**: 置信度驱动的 HITL 决策
5. **Result-Based UI**: 展示数据而非代码
6. **Empirical Analysis**: 基于 477 个真实错误的系统设计

---

## 📞 技术支持

如果遇到问题：
1. 检查 `demo.sqlite` 是否存在（运行 `python3 make_db.py`）
2. 检查依赖是否安装（`pip install -r requirements.txt`）
3. 查看系统日志以了解决策过程
4. 参考 `README_ENHANCED.md` 的故障排除部分

---

**系统状态**: ✅ 所有核心功能已实现并测试通过

**当前运行**: 🌐 Web 界面运行在 http://localhost:8501

**准备演示**: 🎬 随时可以进行现场演示！
