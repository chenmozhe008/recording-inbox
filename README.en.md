[简体中文](README.md) | **English**

# recording-inbox

Drop audio into a Feishu/Lark Drive folder. Your Mac or Windows PC transcribes it locally and publishes AI meeting notes back to Feishu/Lark.

![macOS](https://img.shields.io/badge/macOS-supported-black)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What it does

```text
iPhone / Android / desktop audio
        ↓ upload to Feishu Drive inbox
Mac or Windows checks every minute
        ↓
Local ASR with FunASR / SenseVoice
        ↓
AI notes with DeepSeek or any OpenAI-compatible model
        ↓
Local Markdown + Feishu/Lark online doc
```

It is useful if you record a lot, use Feishu/Lark daily, and want unlimited local transcription without burning through Feishu Minutes quota.

## Highlights

- Local transcription, no per-minute ASR fee.
- macOS and Windows 10/11 support.
- iPhone and Android friendly: any phone that can upload audio to Feishu Drive works.
- Notes are more than transcripts: title, overview, topic outline, todos, chapters, decisions, quotes, and transcript.
- AI-agent friendly: Claude Code / Codex / Cursor can follow `AGENTS.md` to deploy it.

## Quick start

The Chinese README is canonical and more complete: [README.md](README.md)

If you use Claude Code / Codex / Cursor, give it:

```text
Deploy https://github.com/chenmozhe008/recording-inbox for me.
Read AGENTS.md first, choose the macOS or Windows path based on my computer,
and ask me only when you need Feishu auth, folder links, or an API key.
```

Manual setup:

- macOS: see [README.md](README.md#方式-bmacos-手动安装)
- Windows 10/11: see [docs/setup-windows.md](docs/setup-windows.md)
- Phone upload: see [docs/upload-from-phone.md](docs/upload-from-phone.md)

## License

MIT
