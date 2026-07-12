[简体中文](README.md) | **English**

# recording-inbox - open-source AI recording workflow

Upload a recording and let the workflow finish it: audio from a phone or computer enters Feishu/Lark Drive, then a Mac or Windows PC runs local speech-to-text, creates structured AI meeting notes and a separate full transcript, publishes both documents, and sends you one result message with both links.

[![macOS](https://img.shields.io/badge/macOS-supported-black)](docs/setup-macos.md)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-blue)](docs/setup-windows.md)
[![CI](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml/badge.svg)](https://github.com/chenmozhe008/recording-inbox/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Recording is easy. The repetitive work starts afterwards: moving files, waiting for transcription, extracting decisions and action items, naming the result, and putting it back where the team works. `recording-inbox` turns those steps into one restart-safe workflow.

## Why use it?

| Benefit | What it changes |
|---|---|
| Local open-source transcription | FunASR / SenseVoice runs on your computer and does not consume Feishu Minutes transcription quotas |
| Two useful documents | Produces structured AI meeting notes for quick review and a separate full transcript for checking, search, and quotation |
| One inbox for every device | iPhone, Android, downloaded chat audio, and desktop files enter the same Feishu Drive folder |
| Good by default, flexible by scenario | The recommended default uses the mature general notes format; nine optional scenario templates and custom prompts are available |
| Restart-safe automation | Resumes after shutdowns or interruptions and avoids duplicate transcription and duplicate documents |
| Controlled privacy and cost | Audio transcription stays local; transcript text reaches an external API only when AI notes are enabled |
| AI-tool-friendly setup | Use the coding AI tool you already have to follow the installation guide and run checks |

Local transcription is not billed per minute. DeepSeek V4 Flash is the recommended default for notes because its current token pricing is very low, while any OpenAI-compatible Chat Completions provider can be configured. Computer usage and API calls can still have a cost; the project does not promise absolute zero cost.

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
        -> AI notes + separate full transcript
        -> two Feishu documents
        -> one direct Feishu message with two links
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

## Guided setup with an AI tool

Give this prompt to the AI agent tool you already use. Claude Code, Codex, Longxia, WorkBuddy, Trea, Zcode, and similar tools can all follow the same steps.

```text
Deploy https://github.com/chenmozhe008/recording-inbox for me.
Choose the macOS or Windows installation path for my computer,
and stop only when I need to scan Feishu, paste folder links, or enter an API key.
Run setup checks and the simulated tests before enabling background processing.
```

Manual guides:

- [macOS](docs/setup-macos.md)
- [Windows 10/11](docs/setup-windows.md)
- [Phone and desktop upload](docs/upload-from-phone.md)
- [FAQ](docs/faq.md)
- [Project landing page](https://chenmozhe008.github.io/recording-inbox/)

Depending on the Feishu version, Cloud Drive may be called Cloud Docs and the upload button may appear as `+`. Open the inbox folder and choose Upload File.

Both platforms use the same wizard:

```bash
python scripts/setup.py
python scripts/setup_check.py
```

## Output

![Sanitized AI notes preview](docs/assets/sample-minutes-preview.jpg)

The output consists of two documents: AI notes include an overview, outline, todos, chapters, decisions, and quotes; the full transcript remains separate. The recommended default template works for general meetings, while optional templates cover customer conversations, interviews, podcasts, courses, training, projects, research, reviews, and dictation. See the [sample notes](examples/sample-minutes.md) and [sample transcript](examples/sample-transcript.txt).

Single-speaker recordings do not show meaningless `Speaker 1` labels. Multi-speaker recordings keep numbered labels when needed.

The two-document result is meant to support both fast review and careful verification, rather than forcing users to choose between a short summary and raw text.

## Privacy

Transcription runs locally. If AI notes are enabled, transcript text is sent to the OpenAI-compatible API you configure. API keys stay in the local `.env` file and must never be committed.

## Scope

This repository intentionally stays small: ingest, transcription, notes, publishing, and notification. It does not include the private project's task dashboards, approval cards, AI execution system, or iOS app.

## First recording

1. Upload a clear recording longer than 30 seconds to your Feishu inbox.
2. Confirm that the file appears in the inbox.
3. Keep the processing computer powered on and online.
4. Wait for the Feishu completion notification. If it does not arrive, use [troubleshooting](docs/troubleshooting.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Please remove tokens, IDs, local paths, recordings, and transcripts before opening an issue.

If the project saves you time, star it and share the [sanitized output example](examples/sample-minutes.md). Please use only recordings and screenshots that are safe to share.

## License

[MIT](LICENSE)
