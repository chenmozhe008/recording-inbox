#!/usr/bin/env python3
"""公共工具：配置加载、子进程执行、lark-cli 封装。

所有飞书操作都通过 lark-cli 完成（先 `lark-cli auth login` 授权），
本项目不直接持有任何飞书密钥。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def folder_token_from(value: str) -> str:
    """把「飞书文件夹链接」或「folder token」统一成 folder token。

    普通读者从浏览器地址栏复制的是整条链接，形如
    https://xxx.feishu.cn/drive/folder/FldbxxxxxxxxN?from=space_home ，
    让他们自己从中抠出 token 容易出错。这里统一处理：
    - 是链接：取 /folder/ 后面、遇到 ? # / 之前那段，就是 token；
    - 已经是纯 token：原样返回（向后兼容旧配置）。
    """
    value = value.strip()
    match = re.search(r"/folder/([^/?#]+)", value)
    if match:
        return match.group(1)
    return value


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


def _first_http_url(obj: Any) -> str:
    """从飞书返回的嵌套结构里挖出第一个 http 链接，用作卡片按钮跳转地址。"""
    if isinstance(obj, str):
        return obj if obj.startswith("http") else ""
    if isinstance(obj, dict):
        for value in obj.values():
            found = _first_http_url(value)
            if found:
                return found
    if isinstance(obj, list):
        for value in obj:
            found = _first_http_url(value)
            if found:
                return found
    return ""


def notify_webhook(
    config: dict[str, Any],
    *,
    title: str,
    local_path: str = "",
    doc_result: dict[str, Any] | None = None,
    error: str = "",
) -> None:
    """处理完成或失败时，往飞书群「自定义机器人」webhook 发一张卡片。

    读者在飞书群里加一个自定义机器人，把它的 webhook 地址填进 config 的
    feishu_notify_webhook 即可；留空就完全不发（向后兼容旧配置）。
    通知只是锦上添花，任何异常都不该拖垮主流程，所以整段 try/except 吞掉。
    """
    hook = str(config.get("feishu_notify_webhook", "")).strip()
    if not hook or "填" in hook:
        return
    try:
        if error:
            header = {"template": "red",
                      "title": {"tag": "plain_text", "content": "⚠️ 录音处理失败"}}
            lines = [f"**{title}**", "", error[:300]]
            actions: list[dict[str, Any]] = []
        else:
            # 标题特意带「录音」二字：飞书自定义机器人要设关键词校验，
            # 成功卡和失败告警都含「录音」，读者只配一个关键词就够。
            header = {"template": "green",
                      "title": {"tag": "plain_text", "content": "🎙️ 新录音纪要已生成"}}
            lines = [f"**{title}**"]
            if local_path:
                lines += ["", f"本地已保存：{local_path}"]
            doc_url = _first_http_url(doc_result or {})
            if not doc_url:
                # 导入结果里没带链接时自己拼一个：token 从返回里挖，
                # 域名从用户配置的 output 文件夹链接里取（填的是纯 token 就拼不出来，退化为无按钮）。
                data = (doc_result or {}).get("data", {})
                result = data.get("result", {}) if isinstance(data.get("result"), dict) else {}
                token = str(result.get("token") or data.get("token") or "")
                domain = re.search(r"https://[^/\s]+", str(config.get("feishu_output_folder_token", "")))
                if token and domain:
                    doc_url = f"{domain.group(0)}/docx/{token}"
            actions = []
            if doc_url:
                lines += ["", "智能纪要 + 文字记录已整理好，点开查看："]
                actions = [{
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开飞书纪要"},
                        "url": doc_url,
                        "type": "primary",
                    }],
                }]
        elements: list[dict[str, Any]] = [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
        ]
        elements += actions
        card = {"config": {"wide_screen_mode": True}, "header": header, "elements": elements}
        body = json.dumps({"msg_type": "interactive", "card": card}).encode("utf-8")
        request = urllib.request.Request(
            hook, data=body, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=15).read()
    except Exception as exc:
        # 通知只是锦上添花，失败不影响主流程；留一行日志方便排查 webhook 配置问题。
        log(f"飞书通知发送失败（不影响纪要产出）：{exc}")
        return
