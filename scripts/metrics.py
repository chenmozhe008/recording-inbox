#!/usr/bin/env python3
"""Local processing time metrics for ETA calibration."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

from common import atomic_write_json, find_executable, now_iso, resolve_path, run_command


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _read_status(task_dir: Path) -> dict[str, Any]:
    path = task_dir / "status.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_status(task_dir: Path, status: dict[str, Any]) -> None:
    atomic_write_json(task_dir / "status.json", status)


def mark_stage_started(task_dir: Path, stage: str) -> None:
    try:
        status = _read_status(task_dir)
        key = f"{stage}_started_at"
        if not status.get(key):
            status[key] = now_iso()
            _write_status(task_dir, status)
    except Exception:
        return


def record_stage_finished(task_dir: Path, config: dict[str, Any], stage: str, *, backend: str = "") -> None:
    try:
        status = _read_status(task_dir)
        started = _parse_iso(str(status.get(f"{stage}_started_at") or ""))
        finished = _parse_iso(now_iso())
        if not started or not finished:
            return
        manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
        audio_path = task_dir / manifest["audio_file"]
        duration = _audio_duration_seconds(audio_path, config) or 0
        elapsed = max(0.0, (finished - started).total_seconds())
        event = {
            "time": finished.isoformat(timespec="seconds"),
            "recording_id": task_dir.name,
            "stage": stage,
            "audio_duration_seconds": duration,
            "elapsed_seconds": elapsed,
            "speed_ratio": elapsed / duration if duration > 0 else None,
            "backend": backend,
        }
        metrics_path = resolve_path(config.get("processing_metrics_file", "data/state/processing-metrics.jsonl"))
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        _update_summary(config, metrics_path)
    except Exception:
        return


def _audio_duration_seconds(audio_path: Path, config: dict[str, Any]) -> float | None:
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


def _bucket(duration_seconds: float) -> str:
    minutes = duration_seconds / 60
    if minutes <= 15:
        return "0-15m"
    if minutes <= 45:
        return "15-45m"
    if minutes <= 90:
        return "45-90m"
    if minutes <= 180:
        return "90-180m"
    return "180m+"


def _update_summary(config: dict[str, Any], metrics_path: Path) -> None:
    events: list[dict[str, Any]] = []
    for line in metrics_path.read_text(encoding="utf-8").splitlines()[-200:]:
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    buckets: dict[str, dict[str, list[float]]] = {}
    for event in events:
        duration = float(event.get("audio_duration_seconds") or 0)
        elapsed = float(event.get("elapsed_seconds") or 0)
        stage = str(event.get("stage") or "")
        if duration <= 0 or elapsed <= 0 or not stage:
            continue
        buckets.setdefault(_bucket(duration), {}).setdefault(stage, []).append(elapsed)
    summary = {"updated_at": now_iso(), "buckets": {}}
    for bucket, stages in buckets.items():
        summary["buckets"][bucket] = {
            stage: {"count": len(values[-20:]), "median_seconds": round(median(values[-20:]), 1)}
            for stage, values in stages.items()
        }
    atomic_write_json(resolve_path(config.get("processing_speed_file", "data/state/processing-speed.json")), summary)
