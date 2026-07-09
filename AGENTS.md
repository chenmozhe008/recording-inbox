# 给 AI 助手的部署指南

> 你是一个 AI 编程助手（Claude Code / Codex / Cursor 等），你的用户想部署本项目。
> 本文件是为你写的操作手册。用户看的版本是 README.md，两者内容一致，本文只是更利于你执行。

## 项目一句话

iPhone 录音 → 飞书云盘 inbox → 这台 Mac 本地转写（FunASR）→ LLM 纪要 → 本地 Markdown + 飞书文档。全部脚本在 `scripts/`，配置在 `config.json`（从 `config.example.json` 拷贝）。

## 部署流程（按序执行，每步验证后再进下一步）

1. **环境确认**：macOS + Homebrew。没有 brew 时停下来，把 https://brew.sh 的安装命令给用户自己跑（涉及 sudo，不要代跑）。
2. **基础依赖**：`brew install ffmpeg node`，然后 `npm install -g @larksuite/cli`。npm 全局装报权限错时，提示用户配置 npm prefix 或用 sudo，由用户决定。
3. **转写后端**（耗时最长，约 2GB，提前告知用户）：
   ```bash
   python3 -m venv asr-venv
   ./asr-venv/bin/pip install funasr modelscope torch torchaudio
   ```
   装完验证：`./asr-venv/bin/python3 -c "import funasr"`。
4. **飞书授权**：`lark-cli auth login --domain drive,docs` 会输出授权链接/二维码——**必须把它交给用户完成扫码**，你无法代替。完成后 `lark-cli auth status` 验证。
5. **需要用户提供的两个信息**（主动问，不要猜）：
   - inbox 文件夹 token：让用户在飞书云盘建一个文件夹，把文件夹 URL 发给你，你从 URL 提取 token（`/drive/folder/` 后面那串）；
   - DeepSeek API key（可选）：用户没有或不想要 AI 纪要时，把 `config.json` 的 `summary_enabled` 设为 `false`。
6. **写配置**：`cp config.example.json config.json`，填入 token；key 写进 `.env`（格式 `DEEPSEEK_API_KEY=sk-...`）。**绝不把 key 写进 config.json 或提交到 git。**
7. **自检**：`python3 scripts/setup_check.py`，逐条修到全绿。
8. **首次试跑**：让用户往 inbox 文件夹传一个 1 分钟以上的音频，然后 `python3 scripts/run.py`。首次运行会自动下载约 1GB 转写模型（modelscope 国内直连），耐心等待。成功标志：`output/minutes/` 出现 Markdown 文件；配置了输出文件夹的话飞书里出现在线文档。
9. **挂定时**（经用户同意后执行）：
   ```bash
   sed "s|/path/to/recording-inbox|$(pwd)|g" launchd/com.example.recording-inbox.plist > ~/Library/LaunchAgents/com.example.recording-inbox.plist
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.recording-inbox.plist
   ```
   提醒用户：Mac 需保持开机（接电源 + 系统设置里防止自动睡眠）。

## 排错入口

- 每条录音的状态：`data/tasks/<名字>/status.json`（状态机见 README「处理状态」节）
- 运行日志：`logs/run.out.log` / `logs/run.err.log`
- 转写失败：先看 status.json 的 `error` 字段；FunASR 装不上可改走 whisper.cpp 兜底（README 折叠节）
- lark-cli 权限错误：重跑 `lark-cli auth login --domain drive,docs` 补授权

## 边界

- 本项目不需要飞书自建应用（lark-cli 是扫码授权）；只有用户想配 iPhone 快捷指令自动上传时才需要（见 `docs/setup-feishu-app.md` 第三节）。
- 不要替用户修改本仓库以外的任何系统配置。
- 遇到本文没覆盖的问题，读 README 和 `docs/`，仍无解就如实告诉用户，不要瞎猜。
