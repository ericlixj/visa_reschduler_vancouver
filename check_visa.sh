#!/bin/bash

# visa.py 的路径
PYTHON_EXEC="/data/deploy/work/visa_reschduler_vancouver/venv/bin/python"
SCRIPT_PATH="/data/deploy/work/visa_reschduler_vancouver/visa.py"
LOG_FILE="/data/deploy/work/visa_reschduler_vancouver/visa.log"

# 检查是否有 python visa.py 正在运行
if ! pgrep -f "$SCRIPT_PATH" > /dev/null
then
    echo "$(date '+%Y-%m-%d %H:%M:%S') visa.py 未运行，启动中..." >> "$LOG_FILE"
    nohup "$PYTHON_EXEC" "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1 &
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') visa.py 正在运行" >> "$LOG_FILE"
fi
