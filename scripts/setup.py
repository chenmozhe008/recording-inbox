#!/usr/bin/env python3
"""交互式配置向导：只写本机 config.json 和 .env，不上传任何密钥。"""

from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import (
    SUMMARY_TEMPLATES,
    atomic_write_json,
    current_user_open_id,
    folder_token_from,
    load_dotenv,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {str(index): template for index, template in enumerate(SUMMARY_TEMPLATES, start=1)}


def _usable(value: Any) -> str:
    text = str(value or "").strip()
    return text if text.isascii() else ""


def _ask(label: str, default: str = "", *, required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}：").strip() or default
        if value or not required:
            return value
        print("这一项不能为空。")


def _ask_yes_no(label: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input(f"{label} [{hint}]：").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true", "是"}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name} 不是合法 JSON：{exc}") from exc


def merged_config(existing: dict[str, Any]) -> dict[str, Any]:
    template = _read_json(ROOT / "config.example.json")
    executable_defaults = dict(template.get("executables", {}))
    if os.name == "nt":
        executable_defaults.update({
            "lark_cli": "lark-cli.cmd",
            "ffmpeg": "",
            "ffprobe": "",
            "funasr_python": "asr-venv\\Scripts\\python.exe",
        })
    executables = {**executable_defaults, **existing.get("executables", {})}
    return {**template, **existing, "executables": executables}


def write_env_key(key: str, env_name: str = "DEEPSEEK_API_KEY") -> None:
    if not key:
        return
    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    prefix = f"{env_name}="
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.strip().startswith(prefix):
            output.append(prefix + key)
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(prefix + key)
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)


def main() -> int:
    print("\nrecording-inbox 配置向导")
    print("密钥只写入本机 .env，不会显示或提交到 GitHub。\n")

    config_path = ROOT / "config.json"
    config = merged_config(_read_json(config_path))

    inbox_default = _usable(config.get("feishu_inbox_folder_link"))
    while True:
        inbox = _ask("飞书“录音收件箱”文件夹链接", inbox_default, required=True)
        if folder_token_from(inbox):
            break
        print("链接无效，请粘贴浏览器地址栏中含 /drive/folder/ 的整条链接。")
    config["feishu_inbox_folder_link"] = inbox

    output_default = _usable(config.get("feishu_output_folder_link"))
    config["feishu_output_folder_link"] = _ask(
        "飞书“录音结果”文件夹链接（可留空，只保存本地 Markdown）",
        output_default,
    )

    summary_enabled = _ask_yes_no(
        "启用 AI 智能纪要",
        bool(config.get("summary_enabled", True)),
    )
    config["summary_enabled"] = summary_enabled
    if summary_enabled:
        current_template = str(config.get("summary_template") or "meeting")
        reverse = {value: key for key, value in TEMPLATES.items()}
        print("\n纪要模板（直接回车使用默认推荐）：")
        for number, template in TEMPLATES.items():
            print(f"  {number}. {SUMMARY_TEMPLATES[template]}")
        choice = _ask("选择模板", reverse.get(current_template, "1"))
        config["summary_template"] = TEMPLATES.get(choice, current_template)
        config["summary_prompt_file"] = _ask(
            "自定义提示词文件（可留空）",
            str(config.get("summary_prompt_file") or ""),
        )
        key_env = str(config.get("summary_api_key_env") or "DEEPSEEK_API_KEY")
        print(
            "\n模型默认使用 DeepSeek V4 Pro（推荐，纪要质量更好，单次调用通常只有几分钱）。"
            "已有其他 OpenAI 兼容 API 时，可稍后按 docs/setup-api.md 修改配置。"
        )
        load_dotenv()
        if not os.environ.get(key_env):
            key = getpass.getpass(f"模型 API Key（写入 {key_env}，可留空）：").strip()
            write_env_key(key, key_env)

    notify_direct = _ask_yes_no("处理完成后直接发飞书消息给自己", True)
    config["feishu_notify_mode"] = "direct" if notify_direct else "off"
    config["feishu_notify_user_id"] = "auto"
    if notify_direct:
        detected = current_user_open_id(config)
        if detected:
            print("✅ 已自动识别当前飞书账号。")
        else:
            print(
                "⚠️ 尚未识别飞书账号。保存后运行：\n"
                "   lark-cli auth login --domain drive,docs --scope \"im:message.send_as_user im:message\""
            )

    atomic_write_json(config_path, config)
    print(f"\n✅ 配置已保存：{config_path}")
    print("下一步运行环境自检：python scripts/setup_check.py\n")

    if _ask_yes_no("现在运行环境自检", True):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "setup_check.py")]).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
