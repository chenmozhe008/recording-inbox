#!/usr/bin/env python3
"""本地转写：FunASR（SenseVoice，中文效果好、带说话人分离）优先，whisper.cpp 兜底。

产物：任务包目录下的 transcript.txt（人读）+ transcript.json（程序读）。
转写全程在本机进行，录音不经过任何第三方转写服务。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import (
    ROOT,
    atomic_write_json,
    find_executable,
    log,
    resolve_path,
    run_command,
    update_status,
)


def audio_duration_seconds(audio_path: Path, config: dict[str, Any]) -> float | None:
    ffprobe = find_executable(config, "ffprobe", "ffprobe")
    try:
        result = run_command([
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ], timeout=30)
        return float(result.stdout.strip())
    except (RuntimeError, ValueError, subprocess.SubprocessError, OSError):
        return None


def funasr_python(config: dict[str, Any]) -> str | None:
    """装了 funasr 的 python 解释器。没配则用 python3 试探。"""
    configured = str(config.get("executables", {}).get("funasr_python", "")).strip()
    candidate = configured or "python3"
    try:
        run_command([candidate, "-c", "import funasr"], timeout=60)
        return candidate
    except (RuntimeError, subprocess.SubprocessError, OSError):
        return None


def run_funasr(task_dir: Path, audio_path: Path, config: dict[str, Any]) -> str:
    python = funasr_python(config)
    if not python:
        raise RuntimeError("funasr 未安装（pip install funasr modelscope）")
    run_command([
        python,
        str(Path(__file__).with_name("transcribe_funasr.py")),
        "--audio", str(audio_path),
        "--output-dir", str(task_dir),
    ], timeout=int(config.get("transcription_timeout_seconds", 14400)))
    return "funasr-sensevoice"


def whisper_binary(config: dict[str, Any]) -> str:
    configured = str(config.get("executables", {}).get("whisper_cpp", "")).strip()
    if configured and Path(configured).expanduser().is_file():
        return str(Path(configured).expanduser())
    for name in ("whisper-cli", "main"):
        if path := shutil.which(name):
            return path
    raise RuntimeError("未找到 whisper.cpp（brew install whisper-cpp）")


def run_whisper(task_dir: Path, audio_path: Path, config: dict[str, Any]) -> str:
    model_value = str(config.get("executables", {}).get("whisper_model", "")).strip()
    model_path = Path(model_value).expanduser()
    if not model_value or not model_path.is_file():
        raise RuntimeError("未配置 executables.whisper_model（ggml 模型文件路径）")
    ffmpeg = find_executable(config, "ffmpeg", "ffmpeg")
    binary = whisper_binary(config)
    work_dir = task_dir / ".work"
    work_dir.mkdir(exist_ok=True)
    wav_path = work_dir / "input.wav"
    output_prefix = work_dir / "whisper"
    run_command([
        ffmpeg, "-y", "-i", str(audio_path), "-ar", "16000", "-ac", "1", str(wav_path),
    ], timeout=3600)
    run_command([
        binary, "-m", str(model_path), "-f", str(wav_path), "-l", "auto",
        "-oj", "-of", str(output_prefix),
    ], timeout=int(config.get("transcription_timeout_seconds", 14400)))
    raw = json.loads(output_prefix.with_suffix(".json").read_text(encoding="utf-8"))
    segments: list[dict[str, Any]] = []
    for index, item in enumerate(raw.get("transcription", []), start=1):
        offsets = item.get("offsets", {})
        segments.append({
            "id": index,
            "start": float(offsets.get("from", 0)) / 1000,
            "end": float(offsets.get("to", 0)) / 1000,
            "speaker": "speaker_1",
            "text": str(item.get("text", "")).strip(),
        })
    text = "\n".join(
        f"[{int(s['start']) // 3600:02d}:{(int(s['start']) % 3600) // 60:02d}:{int(s['start']) % 60:02d}] {s['text']}"
        for s in segments if s["text"]
    ) + "\n"
    (task_dir / "transcript.txt").write_text(text, encoding="utf-8")
    atomic_write_json(task_dir / "transcript.json", {
        "backend": "whisper.cpp",
        "segments": segments,
        "text": "\n".join(s["text"] for s in segments),
    })
    return "whisper.cpp"


def has_valid_transcript(task_dir: Path) -> bool:
    """转写产物里得有真内容（中英文或数字），全是符号/空白按失败算。"""
    transcript = task_dir / "transcript.txt"
    if not transcript.is_file():
        return False
    text = transcript.read_text(encoding="utf-8")
    return any(ch.isalnum() for ch in text)


def transcribe_task(task_dir: Path, config: dict[str, Any]) -> bool:
    manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
    audio_path = task_dir / manifest["audio_file"]
    if not audio_path.is_file():
        update_status(task_dir, "transcription_failed", "音频文件缺失。", retryable=False)
        return False

    duration = audio_duration_seconds(audio_path, config)
    minimum = float(config.get("minimum_transcription_duration_seconds", 2))
    if duration is not None and duration < minimum:
        update_status(
            task_dir, "transcription_failed",
            f"录音只有 {duration:.1f} 秒，太短，跳过。", retryable=False,
        )
        return False

    update_status(task_dir, "transcribing", "正在本地转写。", duration_seconds=duration)
    errors: list[str] = []
    for runner in (run_funasr, run_whisper):
        try:
            backend = runner(task_dir, audio_path, config)
            if not has_valid_transcript(task_dir):
                raise RuntimeError("转写结果没有有效内容")
            update_status(
                task_dir, "transcript_ready",
                "逐字稿已生成。", transcription_backend=backend,
            )
            return True
        except Exception as exc:
            errors.append(f"{runner.__name__}: {exc}")

    update_status(
        task_dir, "transcription_failed",
        "本地转写失败（FunASR 和 whisper.cpp 都没成功），详见 error 字段。",
        error="；".join(errors)[:800],
    )
    return False


if __name__ == "__main__":
    import sys

    from common import load_config

    if len(sys.argv) != 2:
        raise SystemExit("用法：python3 scripts/transcribe.py <任务包目录>")
    ok = transcribe_task(resolve_path(sys.argv[1]), load_config())
    log("转写成功" if ok else "转写失败")
