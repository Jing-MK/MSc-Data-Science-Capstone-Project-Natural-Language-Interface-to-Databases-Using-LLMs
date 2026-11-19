#!/bin/bash

# Interactive demo script for live presentation
# This runs the HITL (Human-in-the-Loop) correction system

cd "/Users/jing/Desktop/capstone project/Capstone_DIN/Phase_2/nl2sql_system 2"

echo "=========================================="
echo "  NL2SQL Interactive Correction System"
echo "  Human-in-the-Loop (HITL) Demo"
echo "=========================================="
echo ""
echo "Starting interactive demo..."
echo "You will be asked to choose between different SQL results."
echo ""

# Run the interactive demo with TTY
python3 demo_interactive.py

echo ""
echo "Demo completed!"
