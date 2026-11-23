#!/bin/bash
# 检查477案例LLM评估进度

echo "========================================"
echo "477案例LLM评估进度监控"
echo "========================================"
echo ""

# 检查进程是否还在运行
if ps -p 94084 > /dev/null 2>&1; then
    echo "✓ 评估正在运行 (PID: 94084)"
else
    echo "✗ 评估已完成或已停止"
fi

echo ""
echo "最新日志输出 (最后50行):"
echo "----------------------------------------"
tail -50 eval_477_llm_complete.log

echo ""
echo "----------------------------------------"
echo "查看完整日志: tail -f eval_477_llm_complete.log"
echo "检查结果文件: ls -lh data/eval_477_llm_on.json"
echo "========================================"
