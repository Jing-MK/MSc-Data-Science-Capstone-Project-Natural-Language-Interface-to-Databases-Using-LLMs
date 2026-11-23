# 477错题LLM评估状态

**开始时间:** 2026-11-22 23:45
**状态:** ✅ 运行中 (PID: 94084)
**配置:** Qwen API + LLM propose enabled
**预计完成时间:** 60-90分钟

---

## 📊 评估配置

### LLM设置
- **模型:** qwen3.7-plus
- **API:** DashScope (Alibaba Cloud)
- **LLM候选生成:** 启用 (`use_llm_propose: true`)
- **最大轮次:** 4
- **Temperature:** 0.0

### 数据集
- **案例数:** 477个错误查询
- **来源:** eval_results.json (DIN-SQL baseline错误)
- **数据库:** 11个BIRD dev databases

### 四臂评估
1. **no-correction** - 不做任何修正
2. **fix-always** - 总是自动修复（不问用户）
3. **ask-always** - 每次分歧都询问用户
4. **triage (ours)** - 智能triage：自动修复或询问

---

## 🔍 查看进度

### 实时监控
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql-phase2 2"

# 查看实时日志
tail -f eval_477_llm_complete.log

# 检查进度（运行监控脚本）
./check_progress.sh

# 检查进程状态
ps aux | grep 94084
```

### 检查是否完成
```bash
# 查看结果文件是否生成
ls -lh data/eval_477_llm_on.json

# 如果文件存在，查看结果
cat data/eval_477_llm_on.json | python3 -m json.tool | head -50
```

---

## 📈 预期结果

基于文献和前期测试，预期LLM启用后的结果：

### 修复率提升
- **无LLM:** ~2-5% fix rate (rule-based agents only)
- **有LLM:** ~15-30% fix rate (semantic candidate generation)
- **提升:** 3-10倍

### 安全性
- **N_break:** 仍然保持 0 (不破坏正确查询)
- **原因:** Execution-grounded triage确保安全性

### 效率
- **问题减少:** 预计比ask-always少20-30%
- **原因:** LLM生成更好的候选，减少需要询问的情况

### 具体预期 (477案例)
- **N_fix:** 70-140 cases (15-30%)
- **N_break:** 0 cases
- **Questions:** ~600-900 (vs ~900-1200 for ask-always)
- **Q/query:** ~1.3-1.9 (vs ~1.9-2.5 for ask-always)

---

## 📊 结果解读

### 评估输出格式

```
Arm               N_fix  N_break  N_net  Questions  Q/query
-----------------------------------------------------------
no_correction         0        0      0          0     0.00
fix_always           XX        0    +XX          0     0.00
ask_always          YYY        0   +YYY        ZZZ     A.AA
triage              YYY        0   +YYY        WWW     B.BB
```

### 关键指标含义

**N_fix** - 成功修复的错误数
- 衡量系统的修复能力
- 越高越好

**N_break** - 破坏的正确查询数
- **必须为0**（系统设计保证）
- 衡量安全性

**N_net** - 净改进 (N_fix - N_break)
- 总体效果指标
- 应该等于N_fix（因为N_break=0）

**Questions** - 总共问用户的问题数
- 衡量用户交互负担
- 越少越好

**Q/query** - 平均每个查询问几个问题
- **ask-always:** 基准（每次分歧都问）
- **triage:** 应该更少（智能选择何时问）

### 成功标准

✅ **安全性:** N_break = 0 (triage)
✅ **有效性:** N_fix(triage) = N_fix(ask-always) > N_fix(fix-always)
✅ **效率性:** Questions(triage) < Questions(ask-always)

---

## 🎯 评估完成后

### 1. 查看结果文件
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql-phase2 2"
cat data/eval_477_llm_on.json | python3 -m json.tool
```

### 2. 生成详细报告
```python
import json

with open('data/eval_477_llm_on.json') as f:
    results = json.load(f)

print("="*80)
print("477错题LLM评估最终结果")
print("="*80)

for arm_name, arm_results in results.items():
    print(f"\n{arm_name}:")
    print(f"  N_fix: {arm_results['N_fix']}")
    print(f"  N_break: {arm_results['N_break']}")
    print(f"  Questions: {arm_results['questions_asked']}")
    print(f"  Q/query: {arm_results['questions_per_query']:.2f}")
```

### 3. 对比无LLM vs 有LLM
如果需要对比，可以同时查看：
- `data/eval_477_llm_off.json` (无LLM)
- `data/eval_477_llm_on.json` (有LLM)

---

## 🐛 故障排除

### 评估卡住了？
```bash
# 检查进程
ps aux | grep 94084

# 如果卡住，重启评估
pkill -f "run_eval"
python3 -m nl2sql.evaluation.run_eval \
    --cases data/cases_477errors.json \
    --out data/eval_477_llm_on.json
```

### API错误？
检查日志中是否有API错误：
```bash
grep -i "error" eval_477_llm_complete.log
grep -i "exception" eval_477_llm_complete.log
```

常见问题：
- **API key无效:** 检查config.local.yaml
- **Rate limit:** API调用频率限制，等待一段时间
- **Timeout:** 增加timeout_seconds配置

---

## 📞 相关文件

- **配置:** `config.local.yaml`
- **案例:** `data/cases_477errors.json`
- **错题源:** `eval_results.json`
- **数据库:** `dev/dev_databases/`
- **结果:** `data/eval_477_llm_on.json` (完成后生成)
- **日志:** `eval_477_llm_complete.log`
- **进度脚本:** `check_progress.sh`

---

**更新时间:** 2026-11-22 23:45
**状态:** 运行中
**预计完成:** 2026-11-23 01:15 (90分钟后)
