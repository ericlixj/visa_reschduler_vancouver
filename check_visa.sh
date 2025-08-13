#!/bin/bash

# 切换到项目目录
cd /data/deploy/work/visa_reschduler_vancouver || exit 1

# 进程名称
PROCESS_NAME="visa.py"

# 检查进程是否存在
if ! pgrep -f "$PROCESS_NAME" > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME not running, starting..." >> /tmp/visa_cron.log
    /usr/bin/python3 visa.py >> /tmp/visa_cron.log 2>&1 &
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME is running." >> /tmp/visa_cron.log
fi
