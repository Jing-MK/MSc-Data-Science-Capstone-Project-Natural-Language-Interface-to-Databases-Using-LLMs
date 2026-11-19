#!/bin/bash

# Start Web-based HITL Demo
cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"

echo "=========================================="
echo "  Starting NL2SQL Web Demo"
echo "=========================================="
echo ""
echo "📱 Opening web browser..."
echo "🌐 URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

/Users/jing/Library/Python/3.8/bin/streamlit run web_demo.py
