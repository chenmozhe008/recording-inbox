#!/usr/bin/env python3
"""主流程：拉取 → 转写 → 纪要 → 发布。设计成幂等单趟，跑一次推进一轮。

- launchd/cron 每分钟调一次即可（见 launchd/ 目录模板）；
- 用锁文件防止上一轮还没跑完又起一轮（长录音转写可能几十分钟）；
- 发布 = 本地 Markdown（必出）+ 飞书在线文档（配了 feishu_output_folder_token 才发）。
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    import_markdown_as_docx,
    load_config,
    log,
    read_status,
    resolve_path,
    update_status,
)
from minutes import generate_minutes
from pull_inbox import pull
from transcribe import transcribe_task

# 失败态里可自动重试的（retryable=False 除外）；已完成/彻底失败的不再碰
RESUMABLE = {
    "pending": "transcribe",
    "transcribing": "transcribe",        # 上轮中断的，重跑
    "transcription_failed": "transcribe",
    "transcript_ready": "minutes",
    "summarizing": "minutes",
    "minutes_failed": "minutes",
    "minutes_ready": "publish",
    "publish_failed": "publish",
}


def task_dirs(config: dict[str, Any]) -> list[Path]:
    root = resolve_path(config.get("work_dir", "data")) / "tasks"
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and (p / "manifest.json").is_file())


def publish_task(task_dir: Path, config: dict[str, Any]) -> bool:
    manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
    minutes_path = task_dir / "minutes.md"
    day = datetime.now().strftime("%Y-%m-%d")

    # 1) 本地 Markdown 输出（必出）
    output_dir = resolve_path(config.get("output_dir", "output/minutes"))
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / f"{day} {manifest['title']}.md"
    shutil.copyfile(minutes_path, local_path)

    # 2) 飞书在线文档（可选）
    folder_token = str(config.get("feishu_output_folder_token", "")).strip()
    doc_result: dict[str, Any] = {}
    if folder_token and "填" not in folder_token and "留空" not in folder_token:
        try:
            doc_result = import_markdown_as_docx(
                config, minutes_path, f"{day} {manifest['title']}", folder_token,
            )
        except Exception as exc:
            update_status(task_dir, "publish_failed", f"飞书文档导入失败：{exc}"[:300])
            return False

    update_status(
        task_dir, "published", "处理完成。",
        local_output=str(local_path),
        feishu_import=doc_result.get("data", {}),
    )
    log(f"完成：{manifest['title']} -> {local_path.name}")
    return True


def run_once(config: dict[str, Any]) -> None:
    pulled = pull(config)
    if pulled:
        log(f"拉取 {pulled} 个新录音。")
    for task_dir in task_dirs(config):
        status = read_status(task_dir)
        stage = RESUMABLE.get(str(status.get("status", "pending")))
        if stage is None or status.get("retryable") is False:
            continue
        if stage == "transcribe":
            if not transcribe_task(task_dir, config):
                continue
            stage = "minutes"
        if stage == "minutes":
            if not generate_minutes(task_dir, config):
                continue
            stage = "publish"
        if stage == "publish":
            publish_task(task_dir, config)


def main() -> int:
    config = load_config()
    lock_path = resolve_path(config.get("work_dir", "data")) / "state" / "run.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.is_file():
        age = datetime.now().timestamp() - lock_path.stat().st_mtime
        # 锁超过转写超时上限还在 = 上轮进程多半已死，清锁继续
        if age < int(config.get("transcription_timeout_seconds", 14400)) + 600:
            log("上一轮还在运行，本轮跳过。")
            return 0
        log("发现过期锁文件，清除后继续。")
    lock_path.write_text(str(os.getpid()), encoding="utf-8")
    try:
        run_once(config)
    finally:
        lock_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
