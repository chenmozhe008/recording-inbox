# 给 AI 助手的部署指南

你是 Claude Code / Codex / Cursor 这类 AI 编程助手。用户想部署 `recording-inbox`。

目标：让用户把录音上传到飞书 inbox 文件夹后，电脑自动拉取、转写、生成智能纪要并发布到飞书。

## 先判断系统

先运行或询问用户确认：

- macOS：走「macOS 部署」
- Windows 10/11：走「Windows 部署」
- 其他系统：先说明暂未正式支持，可参考 Python 脚本自行适配

不要默认假设用户是 Mac。

## 需要用户提供/操作的事项

这些必须让用户自己完成或提供，不要猜：

1. 飞书扫码授权：`lark-cli auth login --domain drive,docs`
2. 飞书 inbox 文件夹 URL 或 folder token
3. 飞书 output 文件夹 URL 或 folder token（可选）
4. DeepSeek API Key（可选；没有就关闭 `summary_enabled`）

密钥只能写入 `.env`，不要写入 `config.json`，不要提交到 git。

## macOS 部署

```bash
brew install ffmpeg node
npm install -g @larksuite/cli

python3 -m venv asr-venv
./asr-venv/bin/pip install funasr modelscope torch torchaudio soundfile scikit-learn zhconv

lark-cli auth login --domain drive,docs
cp config.example.json config.json
```

写配置后：

```bash
python3 scripts/setup_check.py
python3 scripts/run.py
```

试跑成功后，经用户同意再挂后台：

```bash
sed "s|/path/to/recording-inbox|$(pwd)|g" launchd/com.example.recording-inbox.plist > ~/Library/LaunchAgents/com.example.recording-inbox.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

提醒用户：电脑要接电源并避免自动睡眠。

## Windows 10/11 部署

优先阅读：`docs/setup-windows.md`

最短命令：

```bat
npm install -g @larksuite/cli
lark-cli auth login --domain drive,docs

python -m venv asr-venv
asr-venv\Scripts\pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple funasr modelscope torch torchaudio soundfile scikit-learn zhconv imageio-ffmpeg

copy config.example.json config.json
python scripts\setup_check.py
python scripts\run.py
```

Windows 配置建议：

- `executables.funasr_python` 写 `asr-venv\\Scripts\\python.exe`
- `executables.ffmpeg` 可以留空，程序会尝试用 `imageio-ffmpeg`
- `executables.ffprobe` 可以留空，缺失只会警告
- 如果任务计划里找不到 `lark-cli.cmd`，把 `executables.lark_cli` 改成绝对路径

试跑成功后，经用户同意再让用户双击：

```text
windows\setup_scheduled_task.bat
```

日志：

```text
logs\run.out.log
logs\run.err.log
```

## 手机上传说明

不要把手机端讲复杂。先让用户用最简单路径跑通：

- iPhone：语音备忘录 → 分享 → 飞书 → 保存到 inbox 文件夹
- Android：系统录音机 → 分享 → 飞书 → 保存到 inbox 文件夹
- 微信/电脑文件：下载后直接拖进飞书 inbox 文件夹

更详细说明见 `docs/upload-from-phone.md`。

## 验收标准

部署完成前不要只停在“依赖装好了”。至少完成：

1. `python scripts/setup_check.py` 通过核心检查。
2. 用户往 inbox 上传一条 1 分钟以上音频。
3. `python scripts/run.py` 能处理这条录音。
4. `output/minutes/` 出现 Markdown。
5. 如果配置了 output folder，飞书里出现智能纪要文档。
6. `data/tasks/<录音>/status.json` 状态为 `published`。

## 排错顺序

1. 先看 `scripts/setup_check.py`
2. 再看 `logs/run.err.log`
3. 再看 `data/tasks/<录音>/status.json`
4. lark-cli 权限问题：重跑 `lark-cli auth login --domain drive,docs`
5. Windows 子进程弹黑框或任务计划不执行：确认使用 `run_launcher.py` + `pythonw.exe`

## 边界

- 不要提交 `.env`、`config.json`、`data/`、`logs/`、`output/`。
- 不要替用户做付费、发布、删除云端文件等高风险操作。
- 不要把用户的 API Key 输出到终端或文档里。
- 修改代码后至少跑 `python -m py_compile scripts/*.py run_launcher.py`。
