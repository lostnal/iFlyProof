#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sherpa-onnx 离线说话人分离：输入 16k 单声道 wav，输出 JSON 分段。"""
import os
import sys
import json

import wave

import numpy as np
import sherpa_onnx

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_diarmodels')
SEG_MODEL = os.path.join(BASE, 'sherpa-onnx-pyannote-segmentation-3-0', 'model.onnx')
EMB_MODEL = os.path.join(BASE, 'campplus.onnx')


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'ok': False, 'error': 'usage: diarize_sherpa.py audio.wav [num_speakers]'}))
        return 1
    wav = sys.argv[1]
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    max_s = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    for p in (SEG_MODEL, EMB_MODEL):
        if not os.path.exists(p):
            print(json.dumps({'ok': False, 'error': 'missing model: ' + p}))
            return 1
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=SEG_MODEL)
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=EMB_MODEL),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=max(0, num), threshold=0.5),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not config.validate():
        print(json.dumps({'ok': False, 'error': 'invalid config'}))
        return 1
    with wave.open(wav, 'rb') as f:
        ch = f.getnchannels()
        sw = f.getsampwidth()
        sr = f.getframerate()
        raw = f.readframes(f.getnframes())
    if sw != 2:
        print(json.dumps({'ok': False, 'error': 'need 16-bit wav'}))
        return 1
    if sr != 16000:
        print(json.dumps({'ok': False, 'error': 'need 16k wav, got %d' % sr}))
        return 1
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1)
    if max_s > 0:
        samples = samples[:int(max_s * 16000)]
    sd = sherpa_onnx.OfflineSpeakerDiarization(config)
    result = sd.process(samples).sort_by_start_time()
    segs = [{'start': round(float(s.start), 2), 'end': round(float(s.end), 2), 'spk': int(s.speaker)} for s in result]
    print(json.dumps({'ok': True, 'segments': segs, 'duration': round(len(samples) / 16000.0, 2)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
