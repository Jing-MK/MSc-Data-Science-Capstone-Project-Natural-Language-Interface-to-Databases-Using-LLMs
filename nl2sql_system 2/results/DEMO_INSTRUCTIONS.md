# 🎯 现场演示说明 - NL2SQL 交互式纠错系统

## 📋 准备工作

### 1. 确保数据库已创建
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"
python3 make_db.py
```

### 2. 验证系统可运行
```bash
python3 demo_auto.py  # 测试非交互版本
```

## 🎬 现场演示步骤

### 方式 1: 在你的终端中运行（推荐）

1. **打开新的终端窗口**（不是在 Claude Code 中）

2. **运行交互式演示**:
```bash
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"
python3 demo_interactive.py
```

3. **演示流程**:

#### Case 1: 列名歧义
```
QUESTION: List the names of schools in Alameda county.

系统会显示两个选项：
  Option A: "School Name" 列（完整学校名称）
  Option B: "School" 列（简短学校名称）

👉 你输入: A  （选择完整名称）
```

#### Case 2: 大小写自动修复
```
QUESTION: Schools in Alameda county.

系统会自动修复 'alameda' → 'Alameda'
不需要用户交互，直接显示正确结果
```

### 方式 2: 使用脚本运行

```bash
bash run_interactive.sh
```

## 🎤 演示话术建议

### 开场
> "我们开发了一个智能的 NL2SQL 纠错系统，它能在 SQL 执行前检测问题，并通过人机交互来修复。让我演示一下。"

### Case 1 演示
> "第一个问题：'List the names of schools in Alameda county'
>
> 系统发现数据库中有两个可能的列：'School Name' 和 'School'。
>
> 它不确定用户想要哪个，所以展示两个选项的实际数据让我选择。
>
> 我可以看到 Option A 是完整的学校名称，Option B 是简短名称。
>
> 我选择 A，因为问题要求 'names'，应该是完整名称。
>
> 系统记录了我的选择，以后遇到类似问题会自动使用这个决策。"

### Case 2 演示
> "第二个问题：'Schools in Alameda county'
>
> 预测的 SQL 使用了小写的 'alameda'，但数据库中是 'Alameda'。
>
> 系统自动检测到这个问题并修复了，不需要我的介入。
>
> 这展示了系统的智能：简单的错误自动修复，复杂的歧义才问用户。"

### 总结
> "这个系统的核心价值：
> 1. ✅ 在执行前捕获错误
> 2. ✅ 只在必要时打扰用户
> 3. ✅ 学习用户偏好，减少未来交互
> 4. ✅ 展示实际数据而非 SQL，更易理解"

## 🔧 故障排除

### 如果提示 EOFError
说明没有在交互式终端中运行，需要在真正的终端窗口中运行，不能在后台运行。

### 如果提示数据库错误
运行：
```bash
python3 make_db.py
```

### 如果想看详细日志
编辑 `demo_interactive.py` 第 65 行，改为：
```python
log=lambda m: print(f"  [LOG] {m}")
```

## 📊 演示数据说明

### 数据库内容
- **schools 表**: 4所学校（3所在 Alameda，1所在 Fresno）
- **frpm 表**: 免费午餐数据（通过外键关联）

### 两个测试 Case
1. **列名歧义**: `"School Name"` vs `School`
2. **值大小写错误**: `'alameda'` vs `'Alameda'`

## 🎯 预期演示时间
- **总时长**: 3-5 分钟
- Case 1: 1-2 分钟（需要交互）
- Case 2: 1 分钟（自动修复）
- 讲解: 1-2 分钟

## 💡 额外演示技巧

如果想展示更多 case，可以修改 `demo_interactive.py` 中的 `CASES` 列表，添加新的问题和预测 SQL。

例如：
```python
("How many schools have free meal rate over 30%?",
 "SELECT COUNT(*) FROM schools JOIN frpm ON schools.CDSCode=frpm.CDSCode WHERE \"Free Meal Count (K-12)\"/\"Enrollment (K-12)\" > 0.3")
```

祝演示成功！🎉
