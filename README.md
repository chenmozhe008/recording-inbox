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

代价：需要一台常开机的 Mac（合盖休眠会停，接电源开「防止自动睡眠」）。

## 快速开始

```bash
# 0. 克隆
git clone https://github.com/<你的账号>/recording-inbox.git
cd recording-inbox

# 1. 装依赖
brew install ffmpeg node
npm install -g @larksuite/cli
pip3 install funasr modelscope torch    # 主转写后端（中文效果好，带说话人分离）

# 2. 飞书授权 + 建 inbox 文件夹（详见 docs/setup-feishu-app.md）
lark-cli auth login --domain drive,docs

# 3. 配置
cp config.example.json config.json      # 填 inbox 文件夹 token
echo 'DEEPSEEK_API_KEY=sk-你的key' > .env   # 不想用 LLM 可跳过，config 里关掉 summary_enabled

# 4. 自检（缺什么它会一条条告诉你）
python3 scripts/setup_check.py

# 5. 手动跑一轮试试：往 inbox 文件夹传一个音频，然后
python3 scripts/run.py

# 6. 跑通后挂成每分钟自动运行（见 launchd/ 目录里的模板注释）
```

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

## License

MIT
