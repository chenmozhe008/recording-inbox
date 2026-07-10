**简体中文** | [English](README.en.md)

# recording-inbox

录音丢进飞书文件夹，电脑自动转写并生成一篇像飞书妙记的智能纪要。

![macOS](https://img.shields.io/badge/macOS-supported-black)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 这个项目解决什么问题？

很多人开会、访谈、沟通都会录音，但录完之后通常卡在三件事：

- 飞书妙记免费额度不够；
- 手动上传、转写、整理纪要太麻烦；
- 录音分散在 iPhone、Android、微信、电脑文件夹里，很难统一归档。

`recording-inbox` 的思路很简单：

```text
手机录音 / 微信音频 / 电脑音频
        ↓ 上传到飞书云盘 inbox
Mac 或 Windows 每分钟自动检查
        ↓
本地 FunASR / SenseVoice 转写
        ↓
DeepSeek 等模型生成智能纪要
        ↓
本地 Markdown + 飞书在线文档
```

你只需要把录音放进一个飞书文件夹，剩下的交给电脑。

## 亮点

- **不限量转写**：本地开源模型转写，不消耗飞书妙记时长。
- **跨平台**：Mac、Windows 10、Windows 11 都能跑。
- **手机不挑**：iPhone、Android 都能用，只要能把录音上传到飞书文件夹。
- **更像智能纪要**：不是只吐逐字稿，会生成标题、总览、主题大纲、待办、智能章节、关键决策和金句。
- **隐私更可控**：录音在你的手机、飞书云盘、电脑之间流转；转写在本地跑。
- **适合 AI 助手部署**：Claude Code / Codex / Cursor 可以按 `AGENTS.md` 自动帮你装。

## 适合谁？

适合：

- 每月录音很多，飞书妙记额度不够的人；
- 需要把会议、访谈、电话沟通整理成纪要的人；
- 公司或团队已经在用飞书的人；
- 愿意让一台 Mac 或 Windows 电脑保持开机处理后台任务的人。

不适合：

- 偶尔几条录音，直接用飞书妙记已经够的人；
- 不用飞书的人；
- 不想让电脑保持开机的人。

## 快速开始

### 方式 A：让 AI 助手帮你装（推荐）

把这句话发给 Claude Code / Codex / Cursor：

```text
帮我部署 https://github.com/chenmozhe008/recording-inbox
请先读 AGENTS.md，按我的电脑系统选择 macOS 或 Windows 路径。
需要我扫码、贴飞书文件夹链接、填 DeepSeek Key 时再问我。
```

AI 助手会按系统自动走安装、自检、试跑、后台任务配置。

### 方式 B：macOS 手动安装

```bash
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox

brew install ffmpeg node
npm install -g @larksuite/cli

python3 -m venv asr-venv
./asr-venv/bin/pip install funasr modelscope torch torchaudio soundfile scikit-learn zhconv

lark-cli auth login --domain drive,docs

cp config.example.json config.json
# 编辑 config.json，把飞书 inbox / output 文件夹链接贴进对应字段
# 可选：echo 'DEEPSEEK_API_KEY=sk-你的key' > .env

python3 scripts/setup_check.py
python3 scripts/run.py
```

跑通后挂后台：

```bash
sed "s|/path/to/recording-inbox|$(pwd)|g" launchd/com.example.recording-inbox.plist > ~/Library/LaunchAgents/com.example.recording-inbox.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

### 方式 C：Windows 10/11 手动安装

看完整指南：[docs/setup-windows.md](docs/setup-windows.md)

最短路径：

```bat
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox

npm install -g @larksuite/cli
lark-cli auth login --domain drive,docs

python -m venv asr-venv
asr-venv\Scripts\pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple funasr modelscope torch torchaudio soundfile scikit-learn zhconv imageio-ffmpeg

copy config.example.json config.json
python scripts\setup_check.py
python scripts\run.py
```

跑通后双击：

```text
windows\setup_scheduled_task.bat
```

## 手机怎么上传录音？

详细说明见：[docs/upload-from-phone.md](docs/upload-from-phone.md)

| 设备 | 最简单方式 |
|---|---|
| iPhone | 语音备忘录 → 分享 → 飞书 → 保存到 inbox 文件夹 |
| Android | 系统录音机 → 分享 → 飞书 → 保存到 inbox 文件夹 |
| 微信 / 企业微信音频 | 下载到电脑 → 拖进飞书 inbox 文件夹 |
| 电脑本地音频 | 直接拖进飞书 inbox 文件夹 |

手机只负责上传；电脑负责转写、总结和发布。

## 结果长什么样？

生成的飞书文档会包含：

```text
智能纪要
主题大纲
待办
智能章节
关键决策
金句时刻
文字记录
```

标题会从录音内容归纳，不再只叫“录音-20260710-1711”。单人录音不会硬写“说话人1”；多人讨论会保留说话人编号方便区分观点。

## 配置说明

复制配置：

```bash
cp config.example.json config.json
```

核心字段：

| 字段 | 说明 |
|---|---|
| `feishu_inbox_folder_token` | 手机或电脑上传录音的飞书文件夹；**贴文件夹链接即可**（也兼容填 token） |
| `feishu_output_folder_token` | 智能纪要输出文件夹，贴链接即可；留空则只输出本地 Markdown |
| `feishu_notify_webhook` | 选填：飞书群自定义机器人 webhook，填了就在转写完成/失败时推卡片到群 |
| `summary_enabled` | 是否启用 AI 智能纪要 |
| `summary_api_base` / `summary_model` | OpenAI 兼容模型接口，默认 DeepSeek |
| `executables.funasr_python` | ASR 虚拟环境里的 Python |
| `executables.ffmpeg` | ffmpeg 路径；Windows 可留空并安装 imageio-ffmpeg |

API Key 放 `.env`，不要写进 `config.json`：

```text
DEEPSEEK_API_KEY=sk-你的key
```

## 状态与排错

每条录音会变成 `data/tasks/<录音名>/` 下的任务包。

常用位置：

```text
data/tasks/<录音名>/status.json      单条状态
data/tasks/<录音名>/transcript.txt   文字记录
data/tasks/<录音名>/minutes.md       智能纪要
output/minutes/                      本地归档
logs/run.out.log                     后台正常日志
logs/run.err.log                     后台错误日志
```

状态流：

```text
pending → transcribing → transcript_ready → summarizing → minutes_ready → published
```

自检：

```bash
python scripts/setup_check.py
```

手动跑一轮：

```bash
python scripts/run.py
```

## 常见问题

**Q：为什么不直接用飞书妙记？**
A：妙记很好，但免费时长有限。这个项目用本地模型转写，适合录音量大的人。

**Q：Android 能用吗？**
A：能。Android 只要能把录音上传到飞书 inbox 文件夹，后续流程完全一样。

**Q：Windows 能用吗？**
A：能。Windows 10/11 走任务计划程序，见 [docs/setup-windows.md](docs/setup-windows.md)。

**Q：一定要 DeepSeek 吗？**
A：不一定。`summary_api_base` 和 `summary_model` 支持 OpenAI 兼容接口。不用 AI 纪要也可以把 `summary_enabled` 改成 `false`。

**Q：录音会不会上传到第三方转写服务？**
A：不会。转写在本机跑。只有智能纪要阶段会把逐字稿发给你配置的 LLM 服务；不想发可以关闭 `summary_enabled`。

## 项目结构

```text
scripts/
  run.py                 主流程：拉取 → 转写 → 纪要 → 发布
  pull_inbox.py          从飞书云盘 inbox 拉新录音
  transcribe.py          转写调度：FunASR 优先，whisper.cpp 兜底
  transcribe_funasr.py   SenseVoice 转写 worker，含说话人分离
  minutes.py             智能纪要生成
  setup_check.py         环境自检
  common.py              配置和 lark-cli 封装
docs/
  setup-windows.md       Windows 10/11 安装
  upload-from-phone.md   iPhone / Android 上传
launchd/                 macOS 后台任务
windows/                 Windows 任务计划脚本
```

## Star 一下？

如果这个项目帮你省下了转写会员费，或者让录音整理少折腾一点，欢迎 star。
也欢迎提 issue：最有价值的是不同电脑、不同手机、不同飞书账号环境下的安装反馈。

License: MIT
