# iFlyProof · 转写校对工作台

> 把讯飞听见的分享链接，变成一份可编辑、可回放、可导出的转写稿。

iFlyProof 是一个**本地运行**的转写稿校对工具：粘贴讯飞听见的分享链接，就能一边听录音、一边改文字、整理说话人，最后导出干净的文本或项目文件。所有数据默认只留在你自己的浏览器和电脑里。

---

## 前言

做这个软件，纯粹是**工作所需**。

我们日常的会议、访谈、培训大量使用讯飞听见（录音笔/App）转写。讯飞给出的分享页可以看文字、听录音，但**不能真正编辑**：改错字、调说话人、删掉口水话、把几段录音拼成一份完整稿子，这些都做不了，只能导出 Word 再手工对时间轴，非常低效。

我们也找过市面上的替代方案，结论是**没有特别合适的**：

- 在线转写平台大多要求把音频重新上传到云端，费流量、有隐私顾虑，而且时间码和讯飞原稿对不上；
- 专业的字幕/转写软件（如各类字幕工具）功能很重，学习成本高，对“中文会议 + 讯飞分享链接”这个场景并不顺手；
- 通用的音频编辑软件只能听，不能改转写文字；
- 自己写脚本处理，又很难做到“点文字跳播放、拖进度条反查文字”这种顺手的交互。

于是就有了这个软件：**不重新转写、不上传云端、只在浏览器里把讯飞的分享稿变成可编辑的工作稿**。它不追求大而全，只把“校对一篇转写稿”这件事做顺。

---

## 它解决什么问题

| 痛点 | iFlyProof 的做法 |
| --- | --- |
| 讯飞分享页只能看不能改 | 本地编辑器，文字、发言人、分段、删除都能改 |
| 改完不知道对应哪句录音 | 点文字跳播放、拖进度条反向定位文字、按字估算时间 |
| 录音笔 4 小时自动分段，稿子是碎的 | 最多拼接 3 个分享链接，时间轴自动接续 |
| 说话人分不清 | 本地 AI 自动分说话人（可选），也可手动改名/合并 |
| 改到一半丢了 | 自动保存到浏览器；可导出 `.trp` 项目文件 |
| 不想上传云端 | 音频、文字、模型全部在本机处理 |

---

## 功能一览

- **导入**：粘贴讯飞听见分享链接，自动解析转写文字与时间码；
- **多段拼接**：最多 3 个链接，第二段起时间轴自动偏移接续；
- **音频回放**：点文字跳到对应位置（按字估算，提前 1 秒），拖进度条反查文字；
- **编辑**：双击改字、右键菜单、行内改发言人、分段、删除、撤销（Ctrl/⌘+Z）；
- **说话人**：右侧对照栏改名、别名替换、格式刷刷一片、刷新归并；
- **批量**：按住鼠标拖选多行，复制所有信息 / 仅复制内容 / 删除；
- **历史**：最近 10 个链接，点击直接打开；命中历史时直接载入本地数据，不重复解析；
- **项目文件**：`.trp`（单文件 zip，内含 `state.json` + `audio.mp3`），可保存/打开；
- **自动分说话人**（可选）：本地 sherpa-onnx + CAM++ + 层次聚类，CPU 运行，不上传；
- **纯本地**：无数据库、无账号、无云端，转写稿存在浏览器，音频缓存在 IndexedDB。

---

## 快速开始

### 环境要求

- Python 3.9+（只用标准库，无需安装 Web 框架）；
- 现代浏览器（Chrome / Edge / Safari 均可）；
- 需要能访问讯飞听见的分享页（解析链接时联网）。

### 一键启动（推荐，不用命令行）

**macOS**

1. 下载/克隆项目后，双击 **`iFlyProof.command`**；
2. 服务启动后浏览器会自动打开工作台；
3. 停止：双击 **`stop-iFlyProof.command`**。

> 第一次打开如果 macOS 提示“无法验证开发者”，在文件上右键 → 打开，或到“系统设置 → 隐私与安全性”里允许。

**Windows**

1. 双击 **`iFlyProof.bat`**；
2. 浏览器会自动打开；关闭窗口即停止。

### 命令行启动（备选）

```bash
git clone <your-repo-url> iflyproof
cd iflyproof
python3 server.py
```

然后访问 `http://127.0.0.1:8765/index.html`。

默认只监听 `127.0.0.1`；如需局域网访问：

```bash
HOST=0.0.0.0 PORT=8765 python3 server.py
```

服务启动时会自动打开浏览器；部署在无浏览器的服务器上时，设置 `NO_BROWSER=1`。

### 目录说明

```
.
├── index.html            # 前端单页（工作台全部 UI 与逻辑）
├── server.py             # 本地服务：静态文件 + 讯飞解析 + 音频代理 + 分离接口
├── diarize_sherpa.py     # 本地说话人分离脚本（sherpa-onnx）
├── iFlyProof.command     # macOS 一键启动（双击）
├── iFlyProof.bat         # Windows 一键启动（双击）
├── stop-iFlyProof.command# macOS 停止
├── setup-diarization.command / .bat  # 一键安装说话人分离环境
├── requirements-diarization.txt
├── docs/
│   ├── 使用手册.md
│   └── 开发文档.md
├── README.md
└── LICENSE
```

运行后会生成/需要（已在 `.gitignore` 中忽略）：

```
_diarmodels/       # 说话人模型（需自行下载）
_diarvenv/         # 说话人分离的 Python 虚拟环境
recording_16k.wav  # 大音频/缓存
server.log
```

---

## 自动分说话人（可选）

这个功能依赖 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)，全程本地 CPU 运行，不需要 GPU、不上传音频。

### 一键安装（推荐，不用命令行）

- **macOS**：双击 **`setup-diarization.command`**；
- **Windows**：双击 **`setup-diarization.bat`**。

脚本会自动：

1. 创建 `_diarvenv` 虚拟环境；
2. 安装 `sherpa-onnx`、`numpy`；
3. 下载分割模型（约 7MB）和 CAM++ 向量模型（约 27MB）。

看到“完成”即可，以后不需要再装。

### 手动安装（备选）

```bash
python3 -m venv _diarvenv
_diarvenv/bin/pip install -r requirements-diarization.txt
```

模型目录：

```
_diarmodels/
├── campplus.onnx
└── sherpa-onnx-pyannote-segmentation-3-0/
    └── model.onnx
```

下载地址：

- 分割模型（pyannote segmentation 3.0）：
  <https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2>
- 说话人向量模型（CAM++）：
  - GitHub：<https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx>
  - 国内镜像：<https://hf-mirror.com/Luigi/campplus-zh-en-onnx/resolve/main/campplus_zh_en_fp32.onnx>

把 CAM++ 重命名为 `campplus.onnx` 即可。

### 音频转换

- macOS：系统自带 `afconvert`，无需安装；
- Linux：需要 `ffmpeg`（`apt install ffmpeg` 或发行版对应命令）。

### 使用

编辑页点 **“自动分说话人”**：

1. 输入预计说话人数（2–10）；
2. 输入只分析前多少分钟（`0` = 全部）；
3. 等待完成后，条目会按时间归到“说话人 1/2/3…”，可在右侧对照栏改成真实姓名。

> 模型只在第一次运行时加载；3 小时音频在普通 CPU 上通常需要几分钟，具体取决于机器性能。

## 安全说明（重要）

这个项目定位是**个人/小团队在可信网络里使用**，不是面向公网的多租户服务。

- 服务默认只监听 `127.0.0.1`，请不要直接把它暴露到公网；
- 如果必须远程访问，建议使用 **Tailscale / WireGuard** 等 VPN，或在前端加 **HTTPS + 认证**的反向代理（Caddy / Nginx / 1Panel 均可）；
- 内置了基础防护：
  - 音频代理与差异接口只允许讯飞域名，防止 SSRF；
  - `server.py`、`diarize_sherpa.py`、模型、日志等路径返回 404；
  - `X-Content-Type-Options`、`X-Frame-Options` 等安全头；
  - 分离接口有并发锁，避免被反复点击打满 CPU；
- 转写稿保存在浏览器 `localStorage`，音频缓存在 `IndexedDB`；**服务端不保存用户内容**；
- 请不要在公开仓库中提交任何真实会议内容、音频、密钥或密码。

---

## 常见问题

**Q：解析链接失败？**
A：确认链接是讯飞听见的分享链接（含 `audioId`），且链接未过期。分享链接默认有有效期。

**Q：点文字跳转的位置不太准？**
A：讯飞只给每句的起始时间，字级位置是按字数比例估算的，长句会有偏差，属于正常现象。

**Q：音频加载不出来？**
A：可能是分享链接过期或网络无法访问讯飞。可以先用 `.trp` 项目文件保存一份带音频的副本。

**Q：自动分说话人很慢 / 失败？**
A：确认 `_diarvenv`、`_diarmodels`、`ffmpeg`（Linux）都已就绪；先用“前 2 分钟”试跑，确认链路正常再跑全量。

**Q：换电脑后数据没了？**
A：转写稿存在浏览器本地，换浏览器/清站点数据会丢失。重要稿件请用“保存项目”导出 `.trp`。

**Q：支持其他转写平台吗？**
A：目前只针对讯飞听见的分享链接做了适配；欢迎在 issue 中讨论其他来源。

---

## 技术架构（简版）

```
浏览器（index.html）
  ├─ 解析：POST /api/parse      → server.py 请求讯飞分享接口
  ├─ 音频：GET  /api/audio      → server.py 代理讯飞音频（支持 Range）
  ├─ 分离：POST /api/diarize    → server.py 调 diarize_sherpa.py
  └─ 存储：localStorage + IndexedDB
```

- 后端是一个基于 Python 标准库 `http.server` 的单文件服务，无第三方 Web 依赖；
- 前端是一个无构建步骤的单页 `index.html`，直接由服务端静态托管；
- 说话人分离用 sherpa-onnx（pyannote 分割 + CAM++ 向量 + 层次聚类），通过子进程调用独立虚拟环境。

更详细的模块划分、接口定义和数据模型见 [docs/开发文档.md](docs/开发文档.md)。

---

## 文档

- [使用手册](docs/使用手册.md)：从导入到导出的完整操作说明；
- [开发文档](docs/开发文档.md)：架构、接口、数据模型与扩展点。

---

## 开源协议

本项目采用 [MIT License](LICENSE)。

---

## 致谢

- [讯飞听见](https://www.iflyrec.com/)：转写与分享数据来源；
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)：本地说话人分离；
- [pyannote](https://github.com/pyannote/pyannote-audio) / [3D-Speaker](https://github.com/modelscope/3D-Speaker)：分割与说话人向量模型。

> 本项目与科大讯飞无隶属关系，“讯飞”“iFlytek”等商标归其各自权利人所有。

---

## 开发说明

本项目使用 **DSH（DeepSeek Harness）** 开发。
