**简体中文** | [English](README.en.md)

# recording-inbox

![macOS](https://img.shields.io/badge/platform-macOS-black) ![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

iPhone 随手录音，Mac 自动转写成文字稿和智能纪要，进飞书文档。**转写全程在你自己的 Mac 上跑，免费、不限时长、录音不出自己的设备。**

```
iPhone 录音 ──分享──▶ 飞书云盘 inbox ──每分钟──▶ Mac 拉取
                                                  │
                                          本地转写（FunASR / whisper.cpp）
                                                  │
                                          LLM 智能纪要（DeepSeek，可关）
                                                  │
                                    本地 Markdown ＋ 飞书在线文档
```

## 🚀 安装（选一条路）

**方式 A · 一句话交给 AI 助手（推荐）**

在用 Claude Code / Codex 这类 AI 编程助手的话，新建一个空目录，把下面这句话发给它，然后按它的提示扫个码、发个文件夹链接就装完了：

```text
帮我部署 https://github.com/chenmozhe008/recording-inbox
克隆后按仓库里的 AGENTS.md 一步步来，需要我做的事随时问我。
```

[AGENTS.md](AGENTS.md) 是专门写给 AI 看的部署手册，它知道每一步怎么做、哪些事必须找你。

**方式 B · 手动安装**

会用终端的话照着 [下面的手动安装](#手动安装) 复制粘贴，10 分钟。

## 适不适合你？

同时满足这三条再装：

1. **录音量大**——每月超过飞书妙记免费的 300 分钟，或者不想算账；
2. **日常用飞书**——纪要落进飞书文档才有意义；
3. **有一台可以常开机的 Mac**。

缺任何一条：用妙记 / 通义听悟更省心。三条全中：这是目前唯一「录完不用管、不限量、进飞书」的免费方案。

相比云端转写服务，它多给你两样东西：**隐私**（录音只在你的 iPhone、飞书云盘、Mac 之间流转）和**可改**（纪要提示词就在 `scripts/minutes.py`，想按你的行业黑话总结，改两行就行）。

## 手动安装

前置：一台**常开机**的 Mac（Apple Silicon 最佳；接电源并开「防止自动进入睡眠」）、[Homebrew](https://brew.sh)、飞书账号（个人版即可）、可选的 [DeepSeek](https://platform.deepseek.com) API key（一小时录音的纪要约几分钱）。

```bash
# 0. 克隆
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox

# 1. 基础依赖
brew install ffmpeg node
npm install -g @larksuite/cli

# 2. 转写模型（装在项目内独立 venv，不碰你的系统 Python；约 2GB，耐心等）
python3 -m venv asr-venv
./asr-venv/bin/pip install funasr modelscope torch torchaudio

# 3. 飞书授权（扫码即可，不需要建应用）+ 建 inbox 文件夹拿 token（见 docs/setup-feishu-app.md）
lark-cli auth login --domain drive,docs

# 4. 配置
cp config.example.json config.json      # 填 inbox 文件夹 token
echo 'DEEPSEEK_API_KEY=sk-你的key' > .env   # 不想用 LLM 可跳过，config 里关掉 summary_enabled

# 5. 自检（缺什么它会一条条告诉你）
python3 scripts/setup_check.py

# 6. 手动跑一轮试试：往 inbox 文件夹传一个音频，然后
python3 scripts/run.py
# 首次运行自动下载转写模型（约 1GB，国内直连，实测含下载全程约 2 分钟）

# 7. 跑通后挂成每分钟自动运行（一条命令，自动替换成你的路径）
sed "s|/path/to/recording-inbox|$(pwd)|g" launchd/com.example.recording-inbox.plist > ~/Library/LaunchAgents/com.example.recording-inbox.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

<details>
<summary>（可选）whisper.cpp 兜底后端：FunASR 装不上或英文场景多时用</summary>

```bash
brew install whisper-cpp
mkdir -p models
# 国内用镜像下载模型（约 466MB）；能翻墙可把 hf-mirror.com 换成 huggingface.co
curl -L -o models/ggml-small.bin https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
```

`config.example.json` 里 `whisper_model` 默认就是 `models/ggml-small.bin`，下载完即生效。
</details>

## iPhone 端怎么把录音送进来

三种方式按门槛从低到高，见 [docs/upload-from-iphone.md](docs/upload-from-iphone.md)：

- **手动分享**（零配置）：语音备忘录录完 → 分享 → 飞书 → 存到 inbox 文件夹；
- **快捷指令**（推荐日常）：录完分享给快捷指令，自动上传，全程不打开飞书；
- 配套录音 App 暂未开源，本仓库链路不依赖它。

## 目录结构

```
scripts/
  run.py                 主流程（拉取→转写→纪要→发布），幂等，每分钟跑一轮
  pull_inbox.py          从飞书云盘 inbox 拉新录音，台账防重
  transcribe.py          本地转写调度：FunASR 优先，whisper.cpp 兜底
  transcribe_funasr.py   FunASR 转写 worker（子进程，含说话人分离）
  minutes.py             LLM 智能纪要（Markdown 输出，提示词可改）
  setup_check.py         环境自检
  common.py              配置加载 + lark-cli 封装
docs/                    飞书配置教程 / iPhone 上传教程
launchd/                 macOS 定时任务模板
data/                    运行时任务包（gitignore）
output/minutes/          纪要 Markdown 产物（gitignore）
```

## 处理状态与排错

每条录音是 `data/tasks/` 下的一个目录，`status.json` 记录进度：

`pending → transcribing → transcript_ready → summarizing → minutes_ready → published`

失败态（`transcription_failed` / `minutes_failed` / `publish_failed`）下一轮自动重试；标了 `retryable: false` 的（比如录音太短）不再重试。卡住了就看这个文件加 `logs/run.err.log`。

## FAQ

**Q：为什么必须经过飞书云盘？直接 AirDrop 不行吗？**
A：要的是「录完不用管」。飞书云盘是 iPhone 和 Mac 之间最顺手的异步管道（免费、可靠、快捷指令能自动传）；AirDrop 每次都要人工点。你也可以改 `pull_inbox.py` 换成任何你喜欢的管道（iCloud 目录、WebDAV……），主流程不关心录音从哪来。

**Q：转写质量怎么样？**
A：FunASR 的 SenseVoice 模型中文实测很强，带标点和说话人分离；英文或小语种多的场景 whisper.cpp 更稳。都是本地跑，一小时录音在 Apple Silicon 上通常十几分钟内转完。

**Q：不用 DeepSeek，换别的模型行吗？**
A：行。`config.json` 里 `summary_api_base` / `summary_model` 是任何 OpenAI 兼容接口都能填的，key 写在 `.env`。

**Q：作者自己用的版本和这个有什么区别？**
A：作者的私人版本在这条链路之后还有一大截：纪要自动提取待办、飞书卡片确认、AI 自动执行任务、结果审过闭环、台账看板。那些和个人工作流耦合太深，不适合开源。这个仓库是其中「人人用得上」的部分。

---

> 本项目是一篇公众号文章的配套仓库（文章链接见仓库简介），定位「一个周末能跑通的教程项目」，不承诺长期维护，issue 随缘。License: MIT
