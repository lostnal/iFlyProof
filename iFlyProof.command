#!/bin/bash
# iFlyProof 一键启动（macOS）：双击运行，启动本地服务并打开浏览器。
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "没有找到 python3。请先安装 Python 3.9 或更高版本（python.org 或 Homebrew）。" buttons {"好"} with title "iFlyProof"'
  exit 1
fi

# 已经在运行就直接打开
if curl -s -o /dev/null --max-time 2 http://127.0.0.1:8765/index.html; then
  open "http://127.0.0.1:8765/index.html"
  exit 0
fi

nohup env NO_BROWSER=1 python3 server.py >> server.log 2>&1 &
sleep 1
open "http://127.0.0.1:8765/index.html"
