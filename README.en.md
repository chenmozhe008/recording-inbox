[简体中文](README.md) | **English**

# recording-inbox - open-source AI recording workflow

Upload a recording and let the workflow finish it: audio from a phone or computer enters Feishu/Lark Drive, then a Mac or Windows PC runs local speech-to-text, creates structured AI meeting notes, publishes a document, and sends you the result.

[![macOS](https://img.shields.io/badge/macOS-supported-black)](docs/setup-macos.md)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](docs/setup-windows.md)
[![CI](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml/badge.svg)](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Recording is easy. The repetitive work starts afterwards: moving files, waiting for transcription, extracting decisions and action items, naming the result, and putting it back where the team works. `recording-inbox` turns those steps into one restart-safe workflow.

## Why use it?

| Benefit | What it changes |
|---|---|
| Local open-source transcription | FunASR / SenseVoice runs on your computer and does not consume Feishu Minutes transcription quotas |
| More than a transcript | Produces a title, overview, outline, action items, chapters, decisions, quotes, and transcript |
| One inbox for every device | iPhone, Android, downloaded chat audio, and desktop files enter the same Feishu Drive folder |
| Notes that fit your work | Built-in meeting, interview, course, and project templates, plus fully editable prompts |
| Restart-safe automation | Resumes after shutdowns or interruptions and avoids duplicate transcription and duplicate documents |
| Controlled privacy and cost | Audio transcription stays local; transcript text reaches an external API only when AI notes are enabled |
| AI-agent-friendly setup | Codex, Claude Code, or Cursor can follow the repository's deployment and validation guide |

Local transcription is not billed per minute, but computer usage and the optional AI notes API may still have a cost. The project aims for control and sustainability, not an unrealistic promise of zero cost.

## Good fits

- frequent meetings that need structured notes rather than raw text;
- long interviews, research sessions, and customer conversations;
- courses, training, livestreams, or podcasts that need an accumulating text archive;
- teams already working in Feishu/Lark;
- workflows that need custom terminology, note structure, or action-item rules.

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

## recording-inbox or Feishu Minutes?

| Situation | Better default |
|---|---|
| A few occasional recordings and the smoothest mobile experience | Feishu Minutes |
| Many long recordings or insufficient transcription quota | recording-inbox |
| Custom note structures and domain terminology | recording-inbox |
| No Feishu/Lark usage | another tool |

This project is not a full clone of Feishu Minutes. It focuses on a narrower workflow: high-volume local transcription, customizable notes, and results returned to Feishu/Lark.

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
- [FAQ](docs/faq.md)
- [Project landing page](https://chenmozhe008.github.io/recording-inbox/)

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

The result is meant to be a working document that can be scanned, searched, shared, and acted on, rather than raw text that must be processed again.

## Privacy

Transcription runs locally. If AI notes are enabled, transcript text is sent to the OpenAI-compatible API you configure. API keys stay in the local `.env` file and must never be committed.

## Scope

This repository intentionally stays small: ingest, transcription, notes, publishing, and notification. It does not include the private project's task dashboards, approval cards, AI execution system, or iOS app.

## Validation status

- CI runs the test suite on Windows, macOS, and Ubuntu with Python 3.11.
- Local Chinese transcription has been exercised with a privacy-safe synthetic recording.
- Restart recovery, notification retry, single-speaker cleanup, template loading, and the simulated pipeline are covered by tests.
- The Feishu direct-message command has passed a dry run; the project does not send real messages without user consent.
- iPhone and Android UI recordings and a first-time novice install remain explicit manual verification items.

See the [validation matrix](docs/validation.md) for evidence and remaining boundaries.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Please remove tokens, IDs, local paths, recordings, and transcripts before opening an issue.

If the project saves you time, star it, share the [sanitized output example](examples/sample-minutes.md), or use the [promotion kit](docs/promotion-kit.md) to describe a real experience without overstating unverified capabilities.

## License

[MIT](LICENSE)
