#!/usr/bin/env python3
"""公共工具：配置加载、子进程执行、lark-cli 封装。

所有飞书操作都通过 lark-cli 完成（先 `lark-cli auth login` 授权），
本项目不直接持有任何飞书密钥。
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_dotenv() -> None:
    """把项目根目录 .env 的键值读进环境变量（不覆盖已存在的）。"""
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config() -> dict[str, Any]:
    config_path = ROOT / "config.json"
    if not config_path.is_file():
        raise SystemExit("缺少 config.json：请先 `cp config.example.json config.json` 并填写。")
    load_dotenv()
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_path(value: str | Path) -> Path:
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else ROOT / path


def find_executable(config: dict[str, Any], key: str, fallback: str) -> str:
    configured = str(config.get("executables", {}).get(key, "")).strip()
    return configured or fallback


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 600,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, **(extra_env or {})}
    kwargs: dict[str, Any] = {
        "cwd": str(cwd) if cwd else None,
        "env": env,
        "capture_output": True,
        "text": True,
        "timeout": timeout,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        command,
        **kwargs,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"命令失败（exit {result.returncode}）：{' '.join(command)}\n{result.stderr[:800]}"
        )
    return result


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def update_status(task_dir: Path, status: str, message: str, **extra: Any) -> None:
    """任务包状态机：pending → transcribing → transcript_ready → minutes_ready → published。
    失败态：transcription_failed / minutes_failed / publish_failed（下轮自动重试）。"""
    status_path = task_dir / "status.json"
    existing: dict[str, Any] = {}
    if status_path.is_file():
        try:
            existing = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    atomic_write_json(status_path, {
        **existing,
        "status": status,
        "message": message,
        "updated_at": now_iso(),
        **extra,
    })


def read_status(task_dir: Path) -> dict[str, Any]:
    status_path = task_dir / "status.json"
    if not status_path.is_file():
        return {}
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def log(message: str) -> None:
    print(f"[{now_iso()}] {message}", flush=True)


# ---------- lark-cli 封装 ----------

def lark_json(config: dict[str, Any], args: list[str], *, cwd: Path | None = None, timeout: int = 600) -> dict[str, Any]:
    lark = find_executable(config, "lark_cli", "lark-cli")
    result = run_command([lark, *args], cwd=cwd, timeout=timeout)
    # lark-cli 部分命令会在 JSON 前打一行进度文案，跳过它从第一个 { 开始解析
    stdout = result.stdout
    start = stdout.find("{")
    if start < 0:
        raise RuntimeError(f"lark-cli 未返回 JSON：{stdout[:200]}")
    return json.loads(stdout[start:])


def list_folder(config: dict[str, Any], folder_token: str) -> list[dict[str, Any]]:
    payload = lark_json(config, [
        "drive", "files", "list", "--as", "user",
        "--params", json.dumps({"folder_token": folder_token, "page_size": 200}),
        "--page-all",
    ])
    return payload.get("data", {}).get("files", [])


def drive_download(config: dict[str, Any], file_token: str, dest: Path) -> Path:
    """lark-cli 的 --output 只接受相对路径，所以 cwd 切到目标目录、只传文件名。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    lark = find_executable(config, "lark_cli", "lark-cli")
    run_command([
        lark, "drive", "+download", "--as", "user",
        "--file-token", file_token,
        "--output", f"./{dest.name}",
        "--overwrite",
    ], cwd=dest.parent, timeout=600)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise RuntimeError(f"云盘文件下载失败或为空：{file_token} -> {dest}")
    return dest


def create_folder(config: dict[str, Any], name: str, parent_token: str) -> str:
    payload = lark_json(config, [
        "drive", "+create-folder", "--as", "user",
        "--name", name,
        "--folder-token", parent_token,
    ])
    data = payload.get("data", {})
    token = data.get("folder_token") or data.get("token") or data.get("file_token")
    if not token:
        raise RuntimeError(f"创建文件夹失败：{payload}")
    return str(token)


def drive_move(config: dict[str, Any], file_token: str, folder_token: str) -> None:
    lark_json(config, [
        "drive", "+move", "--as", "user",
        "--file-token", file_token,
        "--folder-token", folder_token,
        "--type", "file",
    ])


def import_markdown_as_docx(config: dict[str, Any], md_path: Path, name: str, folder_token: str) -> dict[str, Any]:
    """把本地 Markdown 导入为飞书在线文档。--file 同样只接受相对路径。"""
    return lark_json(config, [
        "drive", "+import", "--as", "user",
        "--type", "docx",
        "--file", f"./{md_path.name}",
        "--name", name,
        "--folder-token", folder_token,
    ], cwd=md_path.parent, timeout=600)
