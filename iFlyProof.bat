@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  echo 正在启动 iFlyProof...
  python server.py
  pause
  exit /b
)

where py >nul 2>nul
if %errorlevel%==0 (
  echo 正在启动 iFlyProof...
  py -3 server.py
  pause
  exit /b
)

echo 没有找到 Python，请先安装 Python 3.9 或更高版本（python.org）。
pause
