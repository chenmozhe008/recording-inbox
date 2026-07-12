#!/usr/bin/env python3
"""公共工具：配置加载、子进程执行、lark-cli 封装。

所有飞书操作都通过 lark-cli 完成（先 `lark-cli auth login` 授权），
本项目不直接持有任何飞书密钥。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SUMMARY_TEMPLATES: dict[str, str] = {
    "meeting": "默认智能纪要（推荐）",
    "customer": "客户沟通",
    "interview": "访谈整理",
    "podcast": "自媒体 / 播客",
    "course": "课程笔记",
    "training": "培训 / 分享",
    "project": "项目沟通",
    "research": "调研 / 座谈",
    "review": "工作复盘",
    "dictation": "灵感口述",
}


def configure_utf8_console() -> None:
    """Windows 的旧控制台编码可能无法输出中文，不能让日志反过来打断任务。"""
    if os.name != "nt":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


configure_utf8_console()


def folder_token_from(value: str) -> str:
    """把「飞书文件夹链接」统一成 API 需要的文件夹 ID。

    普通读者从浏览器地址栏复制的是整条链接，形如
    https://xxx.feishu.cn/drive/folder/FldbxxxxxxxxN?from=space_home ，
    让他们自己从中抠出 ID 容易出错。这里统一处理：
    - 是链接：取 /folder/ 后面、遇到 ? # / 之前那段；
    - 已经是纯 ID：原样返回（向后兼容旧配置）；
    - 含中文 = 还是 config.example.json 里的占位说明文字，视为没填。
    """
    value = value.strip()
    if not value.isascii():
        return ""
    match = re.search(r"/folder/([^/?#]+)", value)
    if match:
        return match.group(1)
    return value


def configured_folder(config: dict[str, Any], name: str) -> str:
    """读飞书文件夹配置：新字段名 feishu_<name>_folder_link 优先，
    旧字段名 feishu_<name>_folder_token 兼容（已装好的用户不用改配置）。"""
    raw = str(
        config.get(f"feishu_{name}_folder_link")
        or config.get(f"feishu_{name}_folder_token")
        or ""
    )
    return folder_token_from(raw)


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


def lark_auth_status(config: dict[str, Any]) -> dict[str, Any]:
    """返回 lark-cli 的结构化授权状态，供向导、自检和通知共用。"""
    return lark_json(config, ["auth", "status", "--json"], timeout=30)


def current_user_open_id(config: dict[str, Any]) -> str:
    """优先读显式配置，否则从当前 lark-cli 用户身份自动识别 open_id。"""
    configured = str(config.get("feishu_notify_user_id", "")).strip()
    if configured and configured.lower() != "auto" and configured.isascii():
        return configured
    try:
        status = lark_auth_status(config)
        user = status.get("identities", {}).get("user", {})
        if user.get("available"):
            return str(user.get("openId") or "")
    except Exception:
        return ""
    return ""


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


def document_url_from_result(config: dict[str, Any], doc_result: dict[str, Any] | None) -> str:
    """从飞书导入结果或已保存状态恢复可打开的文档链接。"""
    doc_url = _first_http_url(doc_result or {})
    if doc_url:
        return doc_url
    data = (doc_result or {}).get("data", {})
    result = data.get("result", {}) if isinstance(data.get("result"), dict) else {}
    token = str(result.get("token") or data.get("token") or "")
    domain = re.search(r"https://[^/\s]+", str(
        config.get("feishu_output_folder_link")
        or config.get("feishu_output_folder_token")
        or ""
    ))
    return f"{domain.group(0)}/docx/{token}" if token and domain else ""


def _notification_markdown(
    *,
    title: str,
    local_path: str = "",
    doc_url: str = "",
    transcript_url: str = "",
    error: str = "",
) -> str:
    if error:
        return (
            f"**录音处理失败：{title}**\n\n"
            f"{error[:300]}\n\n"
            "可查看状态和日志后重试；如急用，可先使用飞书妙记。"
        )
    lines = [f"**录音转写和智能纪要已完成：{title}**"]
    if doc_url:
        lines += ["", f"[打开智能纪要]({doc_url})"]
    if transcript_url:
        lines += ["", f"[打开文字稿]({transcript_url})"]
    elif local_path:
        lines += ["", f"本地文件：`{local_path}`"]
    return "\n".join(lines)


def _notification_key(title: str, local_path: str, doc_url: str, transcript_url: str, error: str) -> str:
    payload = "|".join((title, local_path, doc_url, transcript_url, error[:300])).encode("utf-8")
    return "recording-inbox-" + hashlib.sha256(payload).hexdigest()[:32]


def _send_direct_notification(
    config: dict[str, Any],
    *,
    title: str,
    local_path: str = "",
    doc_url: str = "",
    transcript_url: str = "",
    error: str = "",
) -> bool:
    user_id = current_user_open_id(config)
    if not user_id:
        raise RuntimeError(
            "无法识别飞书接收人；请重新运行 lark-cli auth login，"
            "或在 config.json 填 feishu_notify_user_id"
        )
    lark = find_executable(config, "lark_cli", "lark-cli")
    markdown = _notification_markdown(
        title=title, local_path=local_path, doc_url=doc_url,
        transcript_url=transcript_url, error=error,
    )
    run_command([
        lark, "im", "+messages-send", "--as", "user",
        "--user-id", user_id,
        "--markdown", markdown,
        "--idempotency-key", _notification_key(title, local_path, doc_url, transcript_url, error),
    ], timeout=60)
    return True


def _valid_webhook(config: dict[str, Any]) -> str:
    hook = str(config.get("feishu_notify_webhook", "")).strip()
    return hook if hook.startswith("http") and hook.isascii() else ""


def _send_webhook_notification(
    config: dict[str, Any],
    *,
    title: str,
    local_path: str = "",
    doc_result: dict[str, Any] | None = None,
    transcript_doc_result: dict[str, Any] | None = None,
    error: str = "",
) -> bool:
    """兼容旧配置：向飞书群自定义机器人 Webhook 发交互卡片。"""
    hook = _valid_webhook(config)
    if not hook:
        return False
    try:
        if error:
            header = {"template": "red",
                      "title": {"tag": "plain_text", "content": "⚠️ 录音处理失败"}}
            lines = [f"**{title}**", "", error[:300]]
            actions: list[dict[str, Any]] = []
        else:
            header = {"template": "green",
                      "title": {"tag": "plain_text", "content": "🎙️ 新录音纪要已生成"}}
            lines = [f"**{title}**"]
            if local_path:
                lines += ["", f"本地已保存：{local_path}"]
            doc_url = document_url_from_result(config, doc_result)
            transcript_url = document_url_from_result(config, transcript_doc_result)
            actions = []
            if doc_url or transcript_url:
                lines += ["", "智能纪要和文字稿已分别整理好："]
                buttons = []
                if doc_url:
                    buttons.append({
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开智能纪要"},
                        "url": doc_url,
                        "type": "primary",
                    })
                if transcript_url:
                    buttons.append({
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "打开文字稿"},
                        "url": transcript_url,
                        "type": "default",
                    })
                actions = [{
                    "tag": "action",
                    "actions": buttons,
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
        return True
    except Exception as exc:
        log(f"飞书通知发送失败（不影响纪要产出）：{exc}")
        return False


def notify_feishu(
    config: dict[str, Any],
    *,
    title: str,
    local_path: str = "",
    doc_result: dict[str, Any] | None = None,
    transcript_doc_result: dict[str, Any] | None = None,
    error: str = "",
) -> bool:
    """默认直达当前飞书账号；旧 Webhook 仅保留兼容和回退。"""
    mode = str(config.get("feishu_notify_mode", "")).strip().lower()
    if not mode:
        mode = "webhook" if _valid_webhook(config) else "direct"
    if mode in {"off", "none", "disabled"}:
        # 已明确关闭时视为无需再处理，避免后台每分钟重复尝试。
        return True

    doc_url = document_url_from_result(config, doc_result)
    transcript_url = document_url_from_result(config, transcript_doc_result)

    if mode == "direct":
        try:
            return _send_direct_notification(
                config,
                title=title,
                local_path=local_path,
                doc_url=doc_url,
                transcript_url=transcript_url,
                error=error,
            )
        except Exception as exc:
            log(f"飞书直达通知失败（不影响纪要产出）：{exc}")
            if _valid_webhook(config):
                return _send_webhook_notification(
                    config,
                    title=title,
                    local_path=local_path,
                    doc_result=doc_result,
                    transcript_doc_result=transcript_doc_result,
                    error=error,
                )
            return False

    if mode == "webhook":
        return _send_webhook_notification(
            config,
            title=title,
            local_path=local_path,
            doc_result=doc_result,
            transcript_doc_result=transcript_doc_result,
            error=error,
        )
    log(f"未知 feishu_notify_mode={mode!r}，已跳过通知。")
    return False


def notify_webhook(
    config: dict[str, Any],
    *,
    title: str,
    local_path: str = "",
    doc_result: dict[str, Any] | None = None,
    transcript_doc_result: dict[str, Any] | None = None,
    error: str = "",
) -> bool:
    """兼容旧调用；新代码使用 notify_feishu。"""
    return _send_webhook_notification(
        config,
        title=title,
        local_path=local_path,
        doc_result=doc_result,
        transcript_doc_result=transcript_doc_result,
        error=error,
    )
