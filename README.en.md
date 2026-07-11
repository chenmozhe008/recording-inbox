[简体中文](README.md) | **English**

# recording-inbox

Drop audio into a Feishu/Lark Drive folder. A Mac or Windows PC transcribes it locally, creates structured AI notes, publishes a Feishu/Lark document, and sends you the result.

[![macOS](https://img.shields.io/badge/macOS-supported-black)](docs/setup-macos.md)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](docs/setup-windows.md)
[![CI](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml/badge.svg)](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## How it works

```text
iPhone / Android / desktop audio
        -> Feishu Drive inbox
        -> local FunASR transcription
        -> AI notes
        -> Feishu document
        -> direct Feishu message
```

The computer may be turned off temporarily. Audio stays in the inbox and resumes after the next login. A powered-off local computer cannot send an offline notification; it notifies you after pickup, completion, or failure.

## Quick start with an AI agent

Give Codex, Claude Code, or Cursor this prompt:

```text
Deploy https://github.com/chenmozhe008/recording-inbox for me.
Read AGENTS.md first, choose macOS or Windows based on my computer,
and stop only when I need to scan Feishu, paste folder links, or enter an API key.
Run setup checks and the simulated tests before enabling background processing.
```

Manual guides:

- [macOS](docs/setup-macos.md)
- [Windows 10/11](docs/setup-windows.md)
- [Phone and desktop upload](docs/upload-from-phone.md)
- [Validation matrix](docs/validation.md)

Feishu's mobile UI changes over time. This repository does not treat a macOS Feishu bundle copied into iOS Simulator as mobile validation. Maintainers should use the [real-device recording checklist](docs/mobile-demo-checklist.md) when refreshing tutorial media.

Both platforms use the same wizard:

```bash
python scripts/setup.py
python scripts/setup_check.py
```

## Output

![Sanitized AI notes preview](docs/assets/sample-minutes-preview.jpg)

Notes include an AI overview, outline, todos, chapters, decisions, quotes, and transcript. Built-in templates cover meetings, interviews, courses, and project discussions. See the [sample notes](examples/sample-minutes.md).

Single-speaker recordings do not show meaningless `Speaker 1` labels. Multi-speaker recordings keep numbered labels when needed.

## Privacy

Transcription runs locally. If AI notes are enabled, transcript text is sent to the OpenAI-compatible API you configure. API keys stay in the local `.env` file and must never be committed.

## Scope

This repository intentionally stays small: ingest, transcription, notes, publishing, and notification. It does not include the private project's task dashboards, approval cards, AI execution system, or iOS app.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Please remove tokens, IDs, local paths, recordings, and transcripts before opening an issue.

## License

[MIT](LICENSE)
