# recording-inbox

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

> 这是一篇公众号文章的配套项目（文章链接见仓库简介），是作者私人自动化系统的精简开源版。
> 定位是「一个周末能跑通的教程项目」，**不承诺长期维护，issue 随缘**。

## 为什么不直接用飞书妙记 / 讯飞 / Otter？

- **额度**：妙记等云端转写按分钟收费或限额（妙记个人版约 300 分钟/月）；本地转写没有表；
- **隐私**：录音文件只在你的 iPhone、你的飞书云盘、你的 Mac 之间流转，不经过第三方转写服务器；
- **可改**：纪要的提示词就在 `scripts/minutes.py` 里，想让它按你的行业黑话总结，改两行就行。

**一句话判断适不适合你**——同时满足这三条再动手：

1. 录音量大（每月超过妙记免费的 300 分钟，或者干脆不想算账）；
2. 你和团队日常用飞书（纪要落进飞书文档才有意义）；
3. 有一台可以常开机的 Mac。

缺任何一条：老实用妙记/通义听悟更省心，这个项目不适合你。三条全中：它是目前唯一「录完不用管、不限量、进飞书」的免费方案。

## 前置条件

- 一台**常开机**的 Mac（Apple Silicon 体验最佳；合盖会停，接电源并在系统设置里开「防止自动进入睡眠」）
- [Homebrew](https://brew.sh)（Mac 的软件包管理器，没装过的先装它，官网一行命令）
- 飞书账号（个人版就行，不需要企业管理员）
- （可选）[DeepSeek](https://platform.deepseek.com) API key，用来生成智能纪要；一小时录音的纪要成本约几分钱

## 快速开始

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
# 首次转写时会自动下载模型（约 1GB，国内直连 modelscope，不用代理）

# 3. 飞书授权 + 建 inbox 文件夹（详见 docs/setup-feishu-app.md）
lark-cli auth login --domain drive,docs

# 4. 配置
cp config.example.json config.json      # 填 inbox 文件夹 token
echo 'DEEPSEEK_API_KEY=sk-你的key' > .env   # 不想用 LLM 可跳过，config 里关掉 summary_enabled

# 5. 自检（缺什么它会一条条告诉你）
python3 scripts/setup_check.py

# 6. 手动跑一轮试试：往 inbox 文件夹传一个音频，然后
python3 scripts/run.py

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

iPhone 端怎么把录音送进 inbox（手动分享 / 快捷指令自动传）：见 `docs/upload-from-iphone.md`。

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

## 处理状态

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

## English

**recording-inbox** turns an iPhone + an always-on Mac into a hands-free meeting-minutes pipeline: record on iPhone → auto-upload to Feishu (Lark) Drive → the Mac picks it up, transcribes **locally** (FunASR / whisper.cpp — free, unlimited, private) → an LLM writes structured minutes → published as Markdown + Feishu docs.

Note: this project is **Feishu/Lark-centric by design** (that's where Chinese teams live). If you don't use Feishu, you'd have to replace the transport layer (`scripts/pull_inbox.py`) — at that point you may be happier with [Buzz](https://github.com/chidiwilliams/buzz) or [Vibe](https://github.com/thewh1teagle/vibe). Docs are Chinese-only; the code comments too. This is a tutorial companion project, maintained casually.

## License

MIT
