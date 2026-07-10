# Windows 10/11 安装指南

这条路径适合 Windows 10 / Windows 11。目标是：电脑每分钟自动检查飞书 inbox，有新录音就本地转写、生成智能纪要并发布到飞书。

## 你需要准备

- Windows 10 或 Windows 11
- Python 3.10+（3.13 已验证可用）
- Node.js 18+
- 飞书账号
- DeepSeek API Key（可选；不用 AI 纪要可关闭）

不需要管理员权限、不需要 MSVC、不需要自己写飞书应用。

## 1. 克隆项目

```bat
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox
```

## 2. 安装 lark-cli

```bat
npm install -g @larksuite/cli
lark-cli auth login --domain drive,docs
lark-cli auth status
```

如果后面定时任务里找不到 `lark-cli.cmd`，把 `config.json` 里的 `executables.lark_cli` 改成它的绝对路径（在 PowerShell 里运行 `where.exe lark-cli.cmd` 就能看到），例如：

```json
"lark_cli": "C:\\Users\\你\\AppData\\Roaming\\npm\\lark-cli.cmd"
```

## 3. 建 ASR 环境

```bat
python -m venv asr-venv
asr-venv\Scripts\pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple funasr modelscope torch torchaudio soundfile scikit-learn zhconv imageio-ffmpeg
```

说明：

- `imageio-ffmpeg` 会自带 `ffmpeg.exe`，避免手动下载 GitHub release。
- 如果 `editdistance` 编译失败，可以先继续看报错；它主要用于评测指标，转写主链路通常不依赖。后续版本会继续把它做成可选依赖。

## 4. 配置飞书文件夹

在飞书云盘建两个文件夹：

- `recording-inbox`：手机上传录音的入口。
- `recording-minutes`：智能纪要输出位置，可选。

打开文件夹，把浏览器地址栏那条链接整条复制下来，写进配置（直接粘整条链接就行，程序自己会处理）：

```bat
copy config.example.json config.json
notepad config.json
```

Windows 推荐这样写：

```json
{
  "feishu_inbox_folder_link": "粘贴你的 inbox 文件夹链接",
  "feishu_output_folder_link": "粘贴你的 output 文件夹链接，留空则只生成本地 Markdown",
  "work_dir": "data",
  "output_dir": "output/minutes",
  "summary_enabled": true,
  "summary_api_base": "https://api.deepseek.com",
  "summary_model": "deepseek-chat",
  "minimum_transcription_duration_seconds": 2,
  "transcription_timeout_seconds": 14400,
  "supported_extensions": [".wav", ".mp3", ".m4a", ".aac", ".mp4", ".mov"],
  "executables": {
    "lark_cli": "lark-cli.cmd",
    "ffmpeg": "",
    "ffprobe": "",
    "funasr_python": "asr-venv\\Scripts\\python.exe",
    "whisper_cpp": "",
    "whisper_model": "models/ggml-small.bin"
  }
}
```

`ffmpeg` 留空也可以，程序会尝试使用 `imageio-ffmpeg`。

## 5. 配置 DeepSeek Key（可选）

```bat
notepad .env
```

写入：

```text
DEEPSEEK_API_KEY=sk-你的key
```

不用 AI 纪要就把 `config.json` 里的 `summary_enabled` 改成 `false`。

## 6. 自检

```bat
python scripts\setup_check.py
```

`ffprobe` 是警告，不影响核心流程。只要 `config.json`、`lark-cli`、至少一个转写后端通过，就可以继续。

## 7. 手动试跑

往飞书 inbox 文件夹上传一条 1 分钟以上录音，然后运行：

```bat
python scripts\run.py
```

成功标志：

- `output/minutes/` 出现 Markdown。
- 如果配置了输出文件夹，飞书里出现一篇智能纪要文档。
- `data/tasks/<录音名>/status.json` 变成 `published`。

首次运行会下载模型，慢一点正常；后面会快很多。

## 8. 开启后台自动处理

双击：

```text
windows\setup_scheduled_task.bat
```

它会注册一个名为 `recording-inbox` 的 Windows 任务计划，每分钟静默运行一次（内部通过 `run_launcher.py` 无窗口地调 `scripts\run.py`，排查问题时知道这一点就够）。

查看日志：

```text
logs\run.out.log
logs\run.err.log
```

卸载后台任务：

```text
windows\remove_scheduled_task.bat
```

## 常见问题

| 问题 | 解决 |
|---|---|
| pip 下载很慢 | 用清华源：`-i https://pypi.tuna.tsinghua.edu.cn/simple` |
| ffmpeg 找不到 | 安装 `imageio-ffmpeg`，或在 `config.json` 填 ffmpeg.exe 绝对路径 |
| ffprobe 警告 | 可忽略，只影响时长预检 |
| 定时任务没反应 | 看 `logs/run.err.log`；确认电脑没有睡眠 |
| lark-cli 未授权 | 重新运行 `lark-cli auth login --domain drive,docs` |
| 飞书没有输出文档 | 检查 `feishu_output_folder_link` 是否填写、账号是否有文件夹权限 |
