#!/usr/bin/env python3
"""主流程：拉取 → 转写 → 纪要 → 发布。设计成幂等单趟，跑一次推进一轮。

- launchd/cron 每分钟调一次即可（见 launchd/ 目录模板）；
- 用锁文件防止上一轮还没跑完又起一轮（长录音转写可能几十分钟）；
- 发布 = 本地 Markdown（必出）+ 飞书在线文档（配了 feishu_output_folder_link 才发）。
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from common import (
    configured_folder,
    import_markdown_as_docx,
    load_config,
    log,
    notify_feishu,
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
    folder_token = configured_folder(config, "output")
    doc_result: dict[str, Any] = {}
    if folder_token:
        try:
            doc_result = import_markdown_as_docx(
                config, minutes_path, f"{day} {manifest['title']}", folder_token,
            )
        except Exception as exc:
            update_status(task_dir, "publish_failed", f"飞书文档导入失败：{exc}"[:300])
            return False

    log(f"完成：{manifest['title']} -> {local_path.name}")
    update_status(
        task_dir, "published", "处理完成。",
        local_output=str(local_path),
        feishu_import=doc_result.get("data", {}),
        notification_sent=False,
    )
    notification_sent = notify_feishu(
        config, title=str(manifest["title"]),
        local_path=str(local_path), doc_result=doc_result,
    )
    if notification_sent:
        update_status(
            task_dir, "published", "处理完成。",
            notification_sent=True,
        )
    return True


def notify_failure(task_dir: Path, config: dict[str, Any]) -> None:
    """某一步失败时，把失败原因也推到飞书群，别让录音石沉大海。

    launchd 每分钟重试一次失败任务，如果每次失败都发一张告警卡，
    群里一小时就是 60 张。所以按「失败状态名」去重：同一个阶段的失败
    只告警一次；等它换了阶段（比如转写修好了、纪要又失败）才会再发。
    """
    status = read_status(task_dir)
    current = str(status.get("status", ""))
    if status.get("failure_notified") == current:
        return
    try:
        manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
        title = str(manifest.get("title") or task_dir.name)
    except Exception:
        title = task_dir.name
    notified = notify_feishu(
        config, title=title,
        error=str(status.get("error") or status.get("message") or "处理失败"),
    )
    if notified:
        update_status(
            task_dir, current, str(status.get("message", "")),
            failure_notified=current,
        )


def retry_pending_notification(task_dir: Path, config: dict[str, Any]) -> None:
    status = read_status(task_dir)
    if status.get("status") != "published" or status.get("notification_sent") is not False:
        return
    try:
        manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
        title = str(manifest.get("title") or task_dir.name)
    except Exception:
        title = task_dir.name
    sent = notify_feishu(
        config,
        title=title,
        local_path=str(status.get("local_output") or ""),
        doc_result={"data": status.get("feishu_import", {})},
    )
    if sent:
        update_status(
            task_dir, "published", str(status.get("message") or "处理完成。"),
            notification_sent=True,
        )


def run_once(config: dict[str, Any]) -> None:
    pulled = pull(config)
    if pulled:
        log(f"拉取 {pulled} 个新录音。")
    for task_dir in task_dirs(config):
        status = read_status(task_dir)
        if status.get("status") == "published":
            retry_pending_notification(task_dir, config)
            continue
        stage = RESUMABLE.get(str(status.get("status", "pending")))
        if stage is None or status.get("retryable") is False:
            continue
        if stage == "transcribe":
            if not transcribe_task(task_dir, config):
                notify_failure(task_dir, config)
                continue
            stage = "minutes"
        if stage == "minutes":
            if not generate_minutes(task_dir, config):
                notify_failure(task_dir, config)
                continue
            stage = "publish"
        if stage == "publish":
            if not publish_task(task_dir, config):
                notify_failure(task_dir, config)


def _lock_pid(lock_path: Path) -> int:
    try:
        raw = lock_path.read_text(encoding="utf-8").strip()
        if raw.startswith("{"):
            return int(json.loads(raw).get("pid") or 0)
        return int(raw)
    except (OSError, ValueError, json.JSONDecodeError, TypeError):
        return 0


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def acquire_run_lock(lock_path: Path, *, fallback_max_age: int) -> bool:
    """原进程已死就立即清锁，让断电/重启后的任务马上续跑。"""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(2):
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pid = _lock_pid(lock_path)
            try:
                age = datetime.now().timestamp() - lock_path.stat().st_mtime
            except OSError:
                continue
            if pid and _pid_is_running(pid):
                return False
            if not pid and age < fallback_max_age:
                return False
            log("发现上轮遗留锁，原进程已结束，清锁后继续。")
            lock_path.unlink(missing_ok=True)
            continue
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"pid": os.getpid(), "created_at": datetime.now().isoformat()}, handle)
        return True
    return False


def release_run_lock(lock_path: Path) -> None:
    if _lock_pid(lock_path) == os.getpid():
        lock_path.unlink(missing_ok=True)


def main() -> int:
    config = load_config()
    lock_path = resolve_path(config.get("work_dir", "data")) / "state" / "run.lock"
    max_age = int(config.get("transcription_timeout_seconds", 14400)) + 600
    if not acquire_run_lock(lock_path, fallback_max_age=max_age):
        log("上一轮还在运行，本轮跳过。")
        return 0
    try:
        run_once(config)
    finally:
        release_run_lock(lock_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
