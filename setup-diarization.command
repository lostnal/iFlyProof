#!/bin/bash
# iFlyProof 说话人分离环境安装（macOS，可选）
# 一般不需要手动运行：首次点“自动分说话人”会自动准备。
cd "$(dirname "$0")" || exit 1

echo "== iFlyProof 说话人分离环境安装（可选） =="
echo "如果网页里首次点“自动分说话人”已经自动准备好，就不需要运行这个。"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ 没有找到 python3，请先安装 Python 3.9+。"
  read -n 1 -s -r -p "按任意键关闭…"
  exit 1
fi

if [ ! -x _diarvenv/bin/python3 ]; then
  echo "→ 创建虚拟环境 _diarvenv …"
  python3 -m venv _diarvenv || { echo "❌ 创建虚拟环境失败"; read -n 1 -s -r -p "按任意键关闭…"; exit 1; }
fi

echo "→ 安装 sherpa-onnx / numpy（首次约 1-3 分钟）…"
_diarvenv/bin/pip install -q -r requirements-diarization.txt || { echo "❌ 依赖安装失败"; read -n 1 -s -r -p "按任意键关闭…"; exit 1; }

mkdir -p _diarmodels/sherpa-onnx-pyannote-segmentation-3-0

if [ ! -f _diarmodels/sherpa-onnx-pyannote-segmentation-3-0/model.onnx ]; then
  if [ -f assets/pyannote-segmentation-3-0.onnx ]; then
    echo "→ 使用内置分割模型…"
    cp assets/pyannote-segmentation-3-0.onnx _diarmodels/sherpa-onnx-pyannote-segmentation-3-0/model.onnx
  else
    echo "→ 下载分割模型（约 7MB）…"
    curl -L --retry 3 -o _diarmodels/seg.tar.bz2 \
      "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2" \
      || echo "⚠️ 分割模型下载失败，可稍后重试"
    tar xjf _diarmodels/seg.tar.bz2 -C _diarmodels 2>/dev/null
  fi
fi

if [ ! -f _diarmodels/campplus.onnx ]; then
  if [ -f assets/campplus.onnx ]; then
    echo "→ 使用内置说话人向量模型…"
    cp assets/campplus.onnx _diarmodels/campplus.onnx
  else
    echo "→ 下载说话人向量模型（约 27MB）…"
    curl -L --retry 3 -o _diarmodels/campplus.onnx \
      "https://hf-mirror.com/Luigi/campplus-zh-en-onnx/resolve/main/campplus_zh_en_fp32.onnx" \
      || echo "⚠️ 向量模型下载失败，可稍后重试"
  fi
fi

echo
if [ -f _diarmodels/sherpa-onnx-pyannote-segmentation-3-0/model.onnx ] && [ -f _diarmodels/campplus.onnx ]; then
  echo "✅ 完成！现在可以双击 iFlyProof.command 启动，在网页里使用“自动分说话人”。"
else
  echo "⚠️ 还有模型没准备好，请检查网络后重新双击本文件。"
fi
echo
read -n 1 -s -r -p "按任意键关闭…"
