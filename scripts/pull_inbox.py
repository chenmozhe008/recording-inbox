#!/usr/bin/env python3
"""从飞书云盘 inbox 拉取新音频，建成本地任务包。

工作方式：
1. 列出 inbox 文件夹里的音频文件（快捷指令 / 手动上传的散装文件）；
2. 没处理过的（台账里没有的）下载到 data/tasks/<任务ID>/，写 manifest + status；
3. 云端原文件挪进 inbox 下的「processed」子文件夹，保持 inbox 干净。

台账是 data/state/inbox-ledger.jsonl，一行一个已处理的 file_token，
删掉某行即可让那个文件下轮重新处理。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import (
    atomic_write_json,
    create_folder,
    drive_download,
    drive_move,
    list_folder,
    log,
    now_iso,
    resolve_path,
    update_status,
)

PROCESSED_FOLDER_NAME = "processed"


def ledger_path(config: dict[str, Any]) -> Path:
    return resolve_path(config.get("work_dir", "data")) / "state" / "inbox-ledger.jsonl"


def load_ledger(config: dict[str, Any]) -> set[str]:
    path = ledger_path(config)
    if not path.is_file():
        return set()
    tokens: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            tokens.add(str(json.loads(line)["file_token"]))
        except (json.JSONDecodeError, KeyError):
            continue
    return tokens


def append_ledger(config: dict[str, Any], file_token: str, name: str) -> None:
    path = ledger_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "file_token": file_token,
            "name": name,
            "pulled_at": now_iso(),
        }, ensure_ascii=False) + "\n")


def safe_task_id(name: str) -> str:
    """文件名 → 目录名：去扩展名、危险字符换下划线、限长。"""
    stem = Path(name).stem
    clean = re.sub(r"[^\w一-鿿-]+", "_", stem).strip("_") or "recording"
    return clean[:60]


def ensure_processed_folder(config: dict[str, Any], inbox_token: str, entries: list[dict[str, Any]]) -> str:
    for entry in entries:
        if entry.get("type") == "folder" and entry.get("name") == PROCESSED_FOLDER_NAME:
            return str(entry.get("token"))
    return create_folder(config, PROCESSED_FOLDER_NAME, inbox_token)


def pull(config: dict[str, Any]) -> int:
    inbox_token = str(config.get("feishu_inbox_folder_token", "")).strip()
    if not inbox_token or "填" in inbox_token:
        log("未配置 feishu_inbox_folder_token，跳过云盘拉取。")
        return 0

    extensions = {ext.lower() for ext in config.get("supported_extensions", [".m4a", ".mp3", ".wav"])}
    seen = load_ledger(config)
    entries = list_folder(config, inbox_token)
    pending = [
        entry for entry in entries
        if entry.get("type") == "file"
        and str(entry.get("token")) not in seen
        and Path(str(entry.get("name", ""))).suffix.lower() in extensions
    ]
    if not pending:
        return 0

    tasks_root = resolve_path(config.get("work_dir", "data")) / "tasks"
    processed_token: str | None = None
    pulled = 0
    for entry in pending:
        file_token = str(entry["token"])
        name = str(entry.get("name", "recording.m4a"))
        task_id = safe_task_id(name)
        task_dir = tasks_root / task_id
        counter = 2
        while task_dir.exists():
            task_dir = tasks_root / f"{task_id}-{counter}"
            counter += 1
        audio_path = task_dir / f"audio{Path(name).suffix.lower()}"
        try:
            drive_download(config, file_token, audio_path)
        except Exception as exc:
            log(f"下载失败（下轮重试）：{name}：{exc}")
            continue

        atomic_write_json(task_dir / "manifest.json", {
            "id": task_dir.name,
            "title": Path(name).stem,
            "source_file_token": file_token,
            "audio_file": audio_path.name,
            "created_at": now_iso(),
        })
        update_status(task_dir, "pending", "已下载，等待转写。")
        append_ledger(config, file_token, name)
        pulled += 1
        log(f"已拉取：{name} -> {task_dir.name}")

        # 云端挪进 processed，失败不影响本地流程（台账已记，不会重复处理）
        try:
            if processed_token is None:
                processed_token = ensure_processed_folder(config, inbox_token, entries)
            drive_move(config, file_token, processed_token)
        except Exception as exc:
            log(f"云端归档失败（不影响处理）：{name}：{exc}")
    return pulled


if __name__ == "__main__":
    from common import load_config

    log(f"本轮拉取 {pull(load_config())} 个新录音。")
