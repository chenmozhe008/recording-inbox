#!/usr/bin/env python3
"""Windows Task Scheduler launcher.

Run this file with pythonw.exe to execute scripts/run.py silently every minute.
It also works on macOS/Linux, but launchd/cron is usually better there.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _python_for_child() -> str:
    current = Path(sys.executable)
    if current.name.lower() == "pythonw.exe":
        python = current.with_name("python.exe")
        if python.is_file():
            return str(python)
    return str(current)


def _timeout_seconds() -> int:
    try:
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        return int(config.get("transcription_timeout_seconds", 14400)) + 900
    except Exception:
        return 15300


def _env() -> dict[str, str]:
    env = os.environ.copy()
    node_dir = env.get("RECORDING_INBOX_NODE_DIR", "").strip()
    if node_dir:
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    return env


def main() -> int:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    out_log = logs_dir / "run.out.log"
    err_log = logs_dir / "run.err.log"
    with out_log.open("a", encoding="utf-8") as out, err_log.open("a", encoding="utf-8") as err:
        out.write(f"[{datetime.now().isoformat(timespec='seconds')}] scheduler tick\n")
        kwargs = {
            "cwd": str(ROOT),
            "stdout": out,
            "stderr": err,
            "timeout": _timeout_seconds(),
            "env": _env(),
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run([_python_for_child(), str(ROOT / "scripts" / "run.py")], **kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
