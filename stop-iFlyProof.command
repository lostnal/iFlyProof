#!/bin/bash
# iFlyProof 停止（macOS）：双击运行，关闭本地服务。
pkill -f 'python3 server.py' >/dev/null 2>&1
osascript -e 'display notification "本地服务已停止" with title "iFlyProof"' 2>/dev/null
