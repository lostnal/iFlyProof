#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""杭汽轮 · 转写校对工作台 —— 本地服务
用法：python3 server.py  （默认 http://127.0.0.1:8765）
"""
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import wave
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT', '8765'))
ALLOWED_HOSTS = ('iflyrec.com', 'shareaudio.iflyrec.com')
BLOCKED_PREFIXES = ('/_', '/server.py', '/diarize_sherpa.py', '/run.sh', '/recording_16k.wav', '/server.log', '/.git')
DIAR_LOCK = threading.Lock()


def url_allowed(u):
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return False
    if p.scheme not in ('http', 'https'):
        return False
    h = (p.hostname or '').lower()
    return any(h == d or h.endswith('.' + d) for d in ALLOWED_HOSTS)



DIAR_VENV = os.path.join(ROOT, '_diarvenv')
DIAR_MODELS = os.path.join(ROOT, '_diarmodels')
SEG_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2'
EMB_URL = 'https://hf-mirror.com/Luigi/campplus-zh-en-onnx/resolve/main/campplus_zh_en_fp32.onnx'
SETUP_STATE = {'state': 'idle', 'step': '', 'message': '', 'progress': 0, 'error': ''}
SETUP_LOCK = threading.Lock()


def _venv_python():
    if os.name == 'nt':
        return os.path.join(DIAR_VENV, 'Scripts', 'python.exe')
    return os.path.join(DIAR_VENV, 'bin', 'python3')


def _venv_pip():
    d = os.path.dirname(_venv_python())
    return os.path.join(d, 'pip.exe' if os.name == 'nt' else 'pip')


def _diar_env_ready():
    return (os.path.exists(_venv_python())
            and os.path.exists(os.path.join(DIAR_MODELS, 'sherpa-onnx-pyannote-segmentation-3-0', 'model.onnx'))
            and os.path.exists(os.path.join(DIAR_MODELS, 'campplus.onnx')))



def _download(url, dst, timeout=180):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dst, 'wb') as f:
        shutil.copyfileobj(r, f)

def _start_setup():
    with SETUP_LOCK:
        if SETUP_STATE.get('state') == 'running':
            return
        if _diar_env_ready():
            SETUP_STATE.update(state='done', step='done', message='环境已就绪', progress=100, error='')
            return
        SETUP_STATE.update(state='running', step='start', message='开始准备…', progress=1, error='')
    threading.Thread(target=_run_setup, daemon=True).start()


def _run_setup():
    try:
        py = None
        for name in ('python3', 'python'):
            p = shutil.which(name)
            if p:
                py = p
                break
        if not py:
            py = sys.executable
        SETUP_STATE.update(step='venv', message='创建虚拟环境…', progress=5)
        if not os.path.exists(_venv_python()):
            subprocess.run([py, '-m', 'venv', DIAR_VENV], check=True, timeout=600)
        SETUP_STATE.update(step='pip', message='安装 sherpa-onnx / numpy…', progress=15)
        req = os.path.join(ROOT, 'requirements-diarization.txt')
        pip_cmd = [_venv_pip()] if os.path.exists(_venv_pip()) else [_venv_python(), '-m', 'pip']
        base = ['install', '-q', '--disable-pip-version-check', '-r', req]
        mirror = os.environ.get('PIP_INDEX_URL') or 'https://pypi.tuna.tsinghua.edu.cn/simple'
        r = subprocess.run(pip_cmd + base + ['-i', mirror], timeout=1800)
        if r.returncode != 0:
            subprocess.run(pip_cmd + base, check=True, timeout=1800)
        os.makedirs(DIAR_MODELS, exist_ok=True)
        seg = os.path.join(DIAR_MODELS, 'sherpa-onnx-pyannote-segmentation-3-0', 'model.onnx')
        if not os.path.exists(seg):
            SETUP_STATE.update(step='seg', message='准备分割模型…', progress=55)
            bundled = os.path.join(ROOT, 'assets', 'pyannote-segmentation-3-0.onnx')
            if os.path.exists(bundled):
                os.makedirs(os.path.dirname(seg), exist_ok=True)
                shutil.copyfile(bundled, seg)
            else:
                tar = os.path.join(DIAR_MODELS, 'seg.tar.bz2')
                _download(SEG_URL, tar)
                with tarfile.open(tar, 'r:bz2') as t:
                    t.extractall(DIAR_MODELS)
        emb = os.path.join(DIAR_MODELS, 'campplus.onnx')
        if not os.path.exists(emb):
            SETUP_STATE.update(step='emb', message='准备说话人向量模型…', progress=75)
            bundled_emb = os.path.join(ROOT, 'assets', 'campplus.onnx')
            if os.path.exists(bundled_emb):
                shutil.copyfile(bundled_emb, emb)
            else:
                _download(EMB_URL, emb)
        SETUP_STATE.update(state='done', step='done', message='环境已就绪', progress=100)
    except Exception as e:
        SETUP_STATE.update(state='error', step='error', message='准备失败', error=str(e), progress=100)

def fmt_time(sec):
    sec = max(0, int(sec))
    return f'{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}'


def http_get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_share(audio_id):
    url = 'https://shareaudio.iflyrec.com/ShareAudioService/v1/audioShares/' + audio_id
    raw = http_get(url, {
        'Referer': 'https://shareaudio.iflyrec.com/appShare/share.html?audioId=' + audio_id,
        'User-Agent': 'Mozilla/5.0',
    })
    return json.loads(raw.decode('utf-8'))


def parse_share(data):
    biz = data.get('biz') or {}
    tr = biz.get('transcriptResult') or {}
    content = tr.get('content')
    if not content:
        raise ValueError('分享里没有转写内容')
    if isinstance(content, str):
        content = json.loads(content)
    ps = content.get('ps') or []
    items = []
    for p in ps:
        words = p.get('words') or []
        text = ''.join(w.get('text') or '' for w in words).strip()
        if not text:
            continue
        pt = p.get('pTime') or [0, 0]
        t = int(pt[0] // 1000)
        items.append({
            't': t,
            'time': fmt_time(t),
            'spk': str(p.get('role') or '1'),
            'text': text,
        })
    duration = int((biz.get('audioDuration') or 0) // 1000)
    return {
        'title': biz.get('audioName') or biz.get('orderName') or '',
        'duration': duration,
        'audioUrl': biz.get('audioPlayUrl') or '',
        'items': items,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write('[srv] ' + fmt % args + '\n')

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path.split('?')[0] == '/api/diarize':
            return self._diarize()
        if self.path.split('?')[0] != '/api/parse':
            return self.send_error(404)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            url = body.get('url') or ''
            m = re.search(r'[?&]audioId=([A-Za-z0-9]+)', url)
            if not m:
                return self._send_json(400, {'ok': False, 'error': '链接里没有 audioId，请确认是讯飞分享链接'})
            data = fetch_share(m.group(1))
            result = parse_share(data)
            result['ok'] = True
            self._send_json(200, result)
        except Exception as e:
            self._send_json(500, {'ok': False, 'error': str(e)})


    def _diarize(self):
        tmpdir = None
        locked = False
        try:
            n = int(self.headers.get('Content-Length') or 0)
            if n > 1024 * 1024:
                return self._send_json(413, {'ok': False, 'error': '请求体过大'})
            body = json.loads(self.rfile.read(n) or b'{}')
            url = body.get('url') or ''
            num = int(body.get('numSpeakers') or 0)
            duration = float(body.get('duration') or 0)
            max_s = float(body.get('maxSeconds') or 0)
            if not url and not duration:
                return self._send_json(400, {'ok': False, 'error': '缺少音频地址'})
            if url and not url_allowed(url):
                return self._send_json(400, {'ok': False, 'error': '只允许讯飞音频域名'})
            if not _diar_env_ready():
                if SETUP_STATE.get('state') == 'error':
                    return self._send_json(500, {'ok': False, 'error': SETUP_STATE.get('error') or '环境准备失败'})
                _start_setup()
                return self._send_json(202, {'ok': False, 'preparing': True, 'message': '首次使用，正在准备本地说话人环境（约 3-5 分钟）…'})
            if not DIAR_LOCK.acquire(False):
                return self._send_json(429, {'ok': False, 'error': '正在分离，请稍候再试'})
            locked = True

            wav = None
            local_wav = os.path.join(ROOT, 'recording_16k.wav')
            if duration and os.path.exists(local_wav):
                try:
                    with wave.open(local_wav, 'rb') as w:
                        ld = w.getnframes() / float(w.getframerate() or 1)
                    if abs(ld - duration) < 10:
                        wav = local_wav
                except Exception:
                    pass

            if not wav:
                if not url:
                    return self._send_json(400, {'ok': False, 'error': '缺少音频地址'})
                tmpdir = tempfile.mkdtemp(prefix='diar_')
                mp3 = os.path.join(tmpdir, 'audio.mp3')
                wav = os.path.join(tmpdir, 'audio.wav')
                headers = {
                    'Referer': 'https://shareaudio.iflyrec.com/',
                    'User-Agent': 'Mozilla/5.0',
                }
                if max_s and duration:
                    try:
                        probe = urllib.request.Request(url, headers=dict(headers, Range='bytes=0-0'))
                        with urllib.request.urlopen(probe, timeout=60) as r:
                            cr = r.headers.get('Content-Range') or ''
                            m2 = re.search(r'/(\d+)', cr)
                            if m2:
                                total = int(m2.group(1))
                                end = min(total - 1, int(total * max_s / duration) + 65536)
                                headers['Range'] = 'bytes=0-%d' % end
                    except Exception:
                        pass
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=300) as r, open(mp3, 'wb') as f:
                    shutil.copyfileobj(r, f)
                if shutil.which('afconvert'):
                    subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16@16000', '-c', '1', mp3, wav],
                                   check=True, timeout=1200, capture_output=True)
                else:
                    ff = shutil.which('ffmpeg') or 'ffmpeg'
                    subprocess.run([ff, '-y', '-i', mp3, '-ar', '16000', '-ac', '1', wav],
                                   check=True, timeout=1200, capture_output=True)

            py = os.path.join(ROOT, '_diarvenv', 'bin', 'python3')
            script = os.path.join(ROOT, 'diarize_sherpa.py')
            if not (os.path.exists(py) and os.path.exists(script)):
                return self._send_json(500, {'ok': False, 'error': '本地说话人环境未安装'})
            cmd = [py, script, wav, str(num)]
            if max_s > 0:
                cmd.append(str(max_s))
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
            stdout = (out.stdout or '').strip()
            if not stdout:
                raise RuntimeError((out.stderr or 'diarize failed')[-800:])
            data = json.loads(stdout.splitlines()[-1])
            return self._send_json(200, data)
        except Exception as e:
            return self._send_json(500, {'ok': False, 'error': str(e)})
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            if locked:
                DIAR_LOCK.release()

    def do_GET(self):
        if self.path.split('?')[0] == '/api/setup-status':
            return self._send_json(200, dict(SETUP_STATE, ok=True))
        if self.path.startswith('/api/audio'):
            return self._proxy_audio()
        return self._serve_static()

    def _serve_static(self):
        req_path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
        req_path = posixpath.normpath('/' + req_path.lstrip('/'))
        for pre in BLOCKED_PREFIXES:
            if req_path == pre or req_path.startswith(pre) or req_path.startswith(pre + '/'):
                return self.send_error(404)
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')
        if not os.path.isfile(path):
            return self.send_error(404)
        size = os.path.getsize(path)
        ctype = self.guess_type(path)
        start, end = 0, size - 1
        rng = self.headers.get('Range')
        partial = False
        if rng:
            m = re.match(r'bytes=(\d*)-(\d*)', rng.strip())
            if m:
                if m.group(1):
                    start = int(m.group(1))
                if m.group(2):
                    end = int(m.group(2))
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', 'bytes */%d' % size)
                    self.end_headers()
                    return
                partial = True
        if partial:
            self.send_response(206)
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        else:
            self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.end_headers()
        with open(path, 'rb') as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(262144, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _proxy_audio(self):
        try:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            src = qs.get('url', [''])[0]
            if not src:
                return self.send_error(400)
            if not url_allowed(src):
                return self.send_error(403)
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://shareaudio.iflyrec.com/',
            }
            rng = self.headers.get('Range')
            if rng:
                headers['Range'] = rng
            req = urllib.request.Request(src, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                code = r.status
                self.send_response(code)
                for k in ('Content-Type', 'Content-Length', 'Content-Range', 'Accept-Ranges'):
                    v = r.headers.get(k)
                    if v:
                        self.send_header(k, v)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
        except Exception:
            try:
                self.send_error(502)
            except Exception:
                pass


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    server = ThreadingHTTPServer((host, PORT), Handler)
    print(f'工作台已启动：http://{host}:{PORT}/index.html')
    if os.environ.get('NO_BROWSER') != '1':
        try:
            import webbrowser
            threading.Timer(1.0, lambda: webbrowser.open(f'http://127.0.0.1:{PORT}/index.html')).start()
        except Exception:
            pass
    server.serve_forever()
