**简体中文** | [English](README.en.md)

# recording-inbox

把录音放进飞书文件夹，电脑自动完成本地转写、智能纪要、飞书归档和结果通知。

[![macOS](https://img.shields.io/badge/macOS-supported-black)](docs/setup-macos.md)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](docs/setup-windows.md)
[![CI](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml/badge.svg)](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

适合会议、采访、课程、客户沟通等大量长录音。转写在自己的 Mac 或 Windows 电脑上运行，不按分钟收费；纪要可以选择会议、访谈、课程、项目模板，也可以直接改提示词。

## 30 秒看懂

```mermaid
flowchart LR
    A[手机录音或电脑音频] --> B[上传到飞书 inbox]
    B --> C[电脑自动接手]
    C --> D[本地 FunASR 转写]
    D --> E[AI 生成智能纪要]
    E --> F[飞书文档归档]
    F --> G[飞书消息通知]
```

电脑临时关机没有关系：录音留在飞书 inbox，开机后自动接着处理。电脑关机时本地程序无法主动发“离线通知”，真正接手、完成或失败后才会通知。

## 它和飞书妙记怎么选？

| 你的情况 | 更合适的选择 |
|---|---|
| 偶尔转几条，希望一步完成 | 先用飞书妙记 |
| 长录音多，免费额度不够 | recording-inbox |
| 想自定义纪要结构和行业术语 | recording-inbox |
| 不使用飞书 | 这个项目不适合 |

本项目不是飞书妙记的完整复刻。它解决的是“大量录音、本地转写、自定义整理、结果仍回到飞书”这条链路。

## 最快安装

### 方式 A：让 AI Agent 帮你安装

把下面这段发给 Codex、Claude Code 或 Cursor：

```text
帮我部署 https://github.com/chenmozhe008/recording-inbox
先读 AGENTS.md，根据我的系统选择 macOS 或 Windows 路径。
需要扫码、粘贴飞书文件夹链接或填写 API Key 时再让我操作，
最后必须跑环境自检和模拟测试。
```

### 方式 B：自己安装

- [macOS 完整安装](docs/setup-macos.md)
- [Windows 10/11 完整安装](docs/setup-windows.md)

安装核心依赖后，两边都用同一个配置向导：

```bash
python scripts/setup.py
python scripts/setup_check.py
```

向导会让你完成：

1. 粘贴飞书 inbox 和纪要输出文件夹链接；
2. 选择会议、访谈、课程或项目沟通模板；
3. 安全输入 DeepSeek API Key（只写本机 `.env`）；
4. 自动识别当前飞书账号，用已有授权直接给自己发结果消息。

不需要手工截取 folder token，也不需要为了通知创建群机器人 Webhook。

## 日常使用

| 录音在哪里 | 推荐上传方法 |
|---|---|
| 电脑、微信或网盘 | 直接拖进飞书 inbox，最简单 |
| iPhone 语音备忘录 | 先存到“文件”，再从飞书 inbox 上传 |
| Android 系统录音机 | 从飞书 inbox 点上传并选择音频 |

第一次使用后，把 inbox 文件夹加入飞书“收藏”，以后不用反复找目录。完整步骤见 [手机和电脑上传教程](docs/upload-from-phone.md)。

飞书移动端按钮会随版本变化，仓库不会用模拟器中的 Mac 版飞书外壳冒充移动端验证。维护者更新截图或视频时，应按 [移动端真机录屏清单](docs/mobile-demo-checklist.md) 走完真实上传闭环。

手机只负责上传，电脑负责转写和整理。默认每分钟检查一次新录音。

## 结果长什么样？

生成的飞书文档包含：

```text
智能纪要
主题大纲
待办
智能章节
关键决策
金句时刻
文字记录
```

标题会根据内容生成；单人录音不会显示没有意义的“说话人1”，多人录音会保留编号区分观点。查看 [脱敏结果示例](examples/sample-minutes.md) 和 [对应文字记录](examples/sample-transcript.txt)。

## 自定义纪要

`config.json` 中选择内置模板：

```json
"summary_template": "meeting"
```

可选值：

- `meeting`：会议纪要
- `interview`：访谈整理
- `course`：课程笔记
- `project`：项目沟通

想完全自定义，就把要求写进一个 Markdown 文件，再填写：

```json
"summary_prompt_file": "prompts/my-template.md"
```

内置模板都在 [prompts](prompts/README.md)，可以直接复制修改。

## 稳定性和恢复

- 每条录音有独立任务包和状态，不靠内存记进度。
- 电脑关机或进程中断后，会从转写、纪要或发布阶段继续。
- 上一轮真的还在运行时，新一轮会跳过，避免重复转写。
- 断电留下的死锁会在开机后立即清理，不会再等待数小时。
- 同一飞书文件只处理一次；原音频处理后移入 inbox 的 `processed` 子文件夹。
- 纪要已发布但通知失败时，只补发通知，不重复创建文档。

状态和排错位置见 [故障恢复指南](docs/troubleshooting.md)。

## 隐私和费用

- 音频转写在本机运行，不上传第三方转写服务。
- 开启智能纪要后，文字记录会发送给你配置的 LLM API。
- 不需要 AI 纪要时，可把 `summary_enabled` 设为 `false`。
- API Key 只放 `.env`，不要粘进聊天、截图、README 或 `config.json`。
- 模型价格和名称会变化，请以 [DeepSeek 官方文档](https://api-docs.deepseek.com/) 为准。

详细配置见 [DeepSeek API 与 Key 安全说明](docs/setup-api.md)。

## 文档导航

- [macOS 安装](docs/setup-macos.md)
- [Windows 10/11 安装](docs/setup-windows.md)
- [飞书文件夹和消息授权](docs/setup-feishu-app.md)
- [iPhone / Android / 电脑上传](docs/upload-from-phone.md)
- [DeepSeek API 与 Key](docs/setup-api.md)
- [故障恢复](docs/troubleshooting.md)
- [纪要模板](prompts/README.md)
- [结果示例](examples/sample-minutes.md)

## 项目边界

这个仓库刻意保持轻量，只做：拉取、转写、纪要、发布和通知。

它不会加入私有主系统里的多维表工作台、每日确认卡、任务分流、Codex/Claude 自动执行或 iOS App。保持边界清楚，普通用户才有可能自己装好并维护。

## 参与和反馈

遇到问题，请按 [贡献指南](CONTRIBUTING.md) 提 Issue。附上系统版本、执行步骤、`status.json` 状态和已脱敏日志，比只说“不能用”更容易定位。

如果这个项目帮你省下了整理录音的时间，欢迎点一个 Star，让更多需要大量录音转写的人看到它。

## License

[MIT](LICENSE)
