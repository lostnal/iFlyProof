@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 set "PY=py -3"

echo == iFlyProof 说话人分离环境安装 ==
echo 这一步只需要做一次。
echo.

if not exist _diarvenv (
  echo 正在创建虚拟环境...
  %PY% -m venv _diarvenv
  if errorlevel 1 (
    echo 创建虚拟环境失败，请确认已安装 Python 3.9+。
    pause
    exit /b 1
  )
)

echo 正在安装依赖（首次约 1-3 分钟）...
_diarvenv\Scripts\pip.exe install -q -r requirements-diarization.txt
if errorlevel 1 (
  echo 依赖安装失败。
  pause
  exit /b 1
)

if not exist _diarmodels mkdir _diarmodels

if not exist _diarmodels\sherpa-onnx-pyannote-segmentation-3-0\model.onnx (
  echo 正在下载分割模型...
  curl -L --retry 3 -o _diarmodels\seg.tar.bz2 "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
  tar xjf _diarmodels\seg.tar.bz2 -C _diarmodels
)

if not exist _diarmodels\campplus.onnx (
  echo 正在下载说话人向量模型...
  curl -L --retry 3 -o _diarmodels\campplus.onnx "https://hf-mirror.com/Luigi/campplus-zh-en-onnx/resolve/main/campplus_zh_en_fp32.onnx"
)

echo.
if exist _diarmodels\sherpa-onnx-pyannote-segmentation-3-0\model.onnx if exist _diarmodels\campplus.onnx (
  echo 完成！现在可以双击 iFlyProof.bat 启动。
) else (
  echo 还有模型没下载完，请检查网络后重新运行本文件。
)
pause
