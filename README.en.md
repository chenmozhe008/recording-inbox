[简体中文](README.md) | **English**

# recording-inbox

Record on your iPhone, and minutes later a structured meeting summary appears in your Feishu (Lark) docs. Transcription runs **entirely on your own Mac** — free, unlimited, and your audio never leaves your devices.

```
iPhone recording ──share──▶ Feishu Drive inbox ──every 60s──▶ Mac pulls it
                                                       │
                                        Local ASR (FunASR / whisper.cpp)
                                                       │
                                        LLM minutes (DeepSeek, optional)
                                                       │
                                     Local Markdown + Feishu online doc
```

> Companion project of a Chinese blog post about building a production-grade personal tool with AI pair-programming — by a film director who doesn't code. Tutorial-grade, casually maintained.

## Is this for you?

All three must be true:

1. You record a lot (more than the ~300 free minutes/month Feishu Minutes gives you);
2. You and your team live in Feishu/Lark (the minutes land there);
3. You have a Mac that can stay awake.

Missing any one? Use Feishu Minutes / Otter instead. If you don't use Feishu at all, look at [Buzz](https://github.com/chidiwilliams/buzz) or [Vibe](https://github.com/thewh1teagle/vibe) — this project's transport layer is Feishu-centric by design (swap `scripts/pull_inbox.py` if you insist).

## Quick start

Prerequisites: an always-on Mac, [Homebrew](https://brew.sh), a Feishu account (personal is fine), and optionally a [DeepSeek](https://platform.deepseek.com) API key for AI minutes.

```bash
git clone https://github.com/chenmozhe008/recording-inbox.git
cd recording-inbox

brew install ffmpeg node
npm install -g @larksuite/cli

# ASR in a project-local venv (~2GB incl. PyTorch; models auto-download on first run)
python3 -m venv asr-venv
./asr-venv/bin/pip install funasr modelscope torch torchaudio

# Feishu auth (device-flow QR, no app registration needed)
lark-cli auth login --domain drive,docs

cp config.example.json config.json      # fill in your inbox folder token
echo 'DEEPSEEK_API_KEY=sk-...' > .env   # optional

python3 scripts/setup_check.py          # tells you exactly what's missing
python3 scripts/run.py                  # process one round manually

# then schedule it every 60s:
sed "s|/path/to/recording-inbox|$(pwd)|g" launchd/com.example.recording-inbox.plist > ~/Library/LaunchAgents/com.example.recording-inbox.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.recording-inbox.plist
```

Getting audio from iPhone into the inbox (manual share / Shortcuts automation): see `docs/upload-from-iphone.md` (Chinese).

## Notes

- Docs and code comments are Chinese-only; the Chinese `README.md` is canonical.
- Pipeline states, retries and troubleshooting: see the Chinese README.
- License: MIT
