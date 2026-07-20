#!/usr/bin/env python3
"""环境自检：一条条告诉你缺什么、怎么补。跑通它再跑主流程。

用法：python3 scripts/setup_check.py
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import (
    SUMMARY_TEMPLATES,
    configured_folder,
    current_user_open_id,
    lark_auth_status,
    lark_json,
    load_dotenv,
    notify_feishu,
)

ROOT = Path(__file__).resolve().parents[1]

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "

TESTED_ASR_BASELINE = {
    "funasr": "1.3.10",
    "modelscope": "1.37.1",
}
ASR_VERSION_PACKAGES = ("funasr", "modelscope", "torch")


def check(label: str, ok: bool, hint: str = "") -> bool:
    print(f"{OK if ok else FAIL} {label}" + ("" if ok else f"\n   → {hint}"))
    return ok


def warn(label: str, ok: bool, hint: str = "") -> bool:
    print(f"{OK if ok else WARN} {label}" + ("" if ok or not hint else f"\n   → {hint}"))
    return ok


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def binary_exists(value: str) -> bool:
    if not value:
        return False
    return bool(shutil.which(value) or resolve_path(value).is_file())


def run_quiet(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    kwargs = {"capture_output": True, "text": True, "timeout": timeout}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(command, **kwargs)


def read_asr_versions(python: str) -> dict[str, str]:
    """Read package metadata inside the configured ASR interpreter."""
    script = (
        "import importlib.metadata as m\n"
        "import json\n"
        f"names = {ASR_VERSION_PACKAGES!r}\n"
        "versions = {}\n"
        "for name in names:\n"
        "    try:\n"
        "        versions[name] = m.version(name)\n"
        "    except m.PackageNotFoundError:\n"
        "        pass\n"
        "print(json.dumps(versions))\n"
    )
    try:
        result = run_quiet([python, "-c", script], timeout=60)
    except (subprocess.SubprocessError, OSError):
        return {}
    if result.returncode != 0:
        return {}
    try:
        payload: Any = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(name).lower(): str(version) for name, version in payload.items() if version}


def asr_baseline_matches(versions: dict[str, str]) -> bool:
    return all(versions.get(name) == version for name, version in TESTED_ASR_BASELINE.items())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查 recording-inbox 运行环境")
    parser.add_argument(
        "--test-notification",
        action="store_true",
        help="自检通过后给当前飞书账号发送一条真实测试消息",
    )
    args = parser.parse_args(argv)
    print("== recording-inbox 环境自检 ==\n")
    print(f"系统：{platform.system()} {platform.release()}\n")
    all_ok = True

    # 1. 配置文件
    config_path = ROOT / "config.json"
    has_config = check(
        "config.json 存在", config_path.is_file(),
        "先运行 python scripts/setup.py 完成配置向导",
    )
    all_ok &= has_config
    if not has_config:
        print("\n== 结论 ==")
        print(f"{FAIL} 请先运行配置向导，再重新执行本脚本。")
        return 1
    config: dict = {}
    if has_config:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            all_ok &= check("config.json 是合法 JSON", False, f"JSON 语法错误：{exc}")
        inbox = str(config.get("feishu_inbox_folder_link") or config.get("feishu_inbox_folder_token") or "")
        all_ok &= check(
            "已填 feishu_inbox_folder_link（录音收件箱链接）", bool(inbox) and inbox.isascii(),
            "把飞书“录音收件箱”文件夹链接贴进 config.json（见 docs/setup-feishu-app.md）",
        )

    # 2. lark-cli
    lark = str(config.get("executables", {}).get("lark_cli", "")) or "lark-cli"
    lark_found = shutil.which(lark) or Path(lark).expanduser().is_file()
    all_ok &= check(
        "lark-cli 已安装", bool(lark_found),
        "npm install -g @larksuite/cli（见 docs/setup-feishu-app.md）",
    )
    auth_payload: dict = {}
    if lark_found:
        try:
            auth_payload = lark_auth_status(config)
            all_ok &= check(
                "lark-cli 已登录授权", True,
                "运行 lark-cli auth login --domain drive,docs 完成授权",
            )
        except (RuntimeError, subprocess.SubprocessError, OSError, json.JSONDecodeError):
            all_ok &= check(
                "lark-cli 已登录授权", False,
                "运行 lark-cli auth login --domain drive,docs 完成授权",
            )

    # 2.5. 输出目录：只读探测，避免旧 token 到真正发布时才暴露。
    output_folder = configured_folder(config, "output")
    if output_folder and lark_found and auth_payload:
        try:
            lark_json(config, [
                "drive", "files", "list", "--as", "user",
                "--folder-token", output_folder, "--page-size", "1",
            ], timeout=30)
            all_ok &= check("飞书“录音结果”文件夹可访问", True)
        except (RuntimeError, subprocess.SubprocessError, OSError, json.JSONDecodeError):
            all_ok &= check(
                "飞书“录音结果”文件夹可访问", False,
                "录音结果文件夹可能已删除或无权限；重新运行 python scripts/setup.py 选择有效文件夹",
            )
    elif output_folder:
        warn("尚未验证飞书“录音结果”文件夹", False, "先完成 lark-cli 登录授权后重新运行自检")
    else:
        warn("未配置飞书“录音结果”文件夹（仅保存本地 Markdown）", False,
             "需要飞书双文档归档时，重新运行 python scripts/setup.py 配置录音结果文件夹")

    # 3. 飞书通知：新安装默认直达当前账号；Webhook 仅兼容旧配置
    notify_mode = str(config.get("feishu_notify_mode", "")).strip().lower()
    webhook = str(config.get("feishu_notify_webhook", "")).strip()
    if not notify_mode:
        notify_mode = "webhook" if webhook.startswith("http") else "direct"
    notification_ready = True
    if notify_mode == "direct":
        user_id = current_user_open_id(config) if lark_found else ""
        notification_ready &= check(
            "已识别飞书消息接收账号", bool(user_id),
            "重新运行 lark-cli auth login，或在 config.json 填 feishu_notify_user_id",
        )
        user_auth = auth_payload.get("identities", {}).get("user", {})
        scopes = str(user_auth.get("scope") or "")
        notification_ready &= check(
            "已授权飞书消息发送权限",
            "im:message.send_as_user" in scopes,
            "运行 lark-cli auth login --scope \"im:message.send_as_user im:message\"",
        )
    elif notify_mode == "webhook":
        notification_ready &= check(
            "飞书群机器人 Webhook 已配置",
            webhook.startswith("http") and webhook.isascii(),
            "填写有效 feishu_notify_webhook，或把 feishu_notify_mode 改成 direct",
        )
    elif notify_mode in {"off", "none", "disabled"}:
        print(f"{OK} 飞书通知已关闭")
    else:
        notification_ready = check(
            "飞书通知模式有效", False,
            "feishu_notify_mode 只能是 direct / webhook / off",
        )
    all_ok &= notification_ready

    # 4. ffmpeg / ffprobe
    ffmpeg = str(config.get("executables", {}).get("ffmpeg", "")) or "ffmpeg"
    ffmpeg_ok = binary_exists(ffmpeg)
    if not ffmpeg_ok and os.name == "nt":
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_ok = Path(imageio_ffmpeg.get_ffmpeg_exe()).is_file()
        except Exception:
            ffmpeg_ok = False
    all_ok &= check(
        "ffmpeg 已安装",
        ffmpeg_ok,
        "macOS: brew install ffmpeg；Windows: asr-venv\\Scripts\\pip install imageio-ffmpeg",
    )

    ffprobe = str(config.get("executables", {}).get("ffprobe", "")) or "ffprobe"
    ffprobe_ok = binary_exists(ffprobe)
    if ffprobe_ok:
        print(f"{OK} ffprobe 已安装")
    else:
        warn(
            "ffprobe 未安装（不影响转写，只会跳过精确时长预检）",
            False,
            "macOS 可 brew install ffmpeg；Windows 可留空或安装完整 ffmpeg 包。",
        )

    # 5. 转写后端：FunASR 或 whisper.cpp 至少一个
    funasr_py = str(config.get("executables", {}).get("funasr_python", "")) or "python3"
    asr_versions = read_asr_versions(funasr_py)
    funasr_ok = bool(asr_versions.get("funasr"))
    whisper_bin = str(config.get("executables", {}).get("whisper_cpp", ""))
    whisper_ok = bool(
        (whisper_bin and Path(whisper_bin).expanduser().is_file())
        or shutil.which("whisper-cli")
    )
    if funasr_ok:
        print(f"{OK} FunASR 可用（主转写，中文效果好）")
        version_text = " / ".join(
            f"{name} {asr_versions[name]}"
            for name in ASR_VERSION_PACKAGES
            if asr_versions.get(name)
        )
        print(f"   ASR 版本：{version_text}")
        warn(
            "FunASR 核心版本与仓库验证基线一致",
            asr_baseline_matches(asr_versions),
            "当前版本不一定有问题；新安装建议按 requirements/asr-macos.txt "
            "或 requirements/asr-windows.txt 重建环境。",
        )
    else:
        print(f"{WARN}FunASR 不可用（请按 requirements/asr-macos.txt 或 asr-windows.txt 安装）")
    if whisper_ok:
        model = str(config.get("executables", {}).get("whisper_model", ""))
        whisper_ok = check(
            "whisper.cpp 模型已配置", bool(model) and Path(model).expanduser().is_file(),
            "下载 ggml 模型并填到 executables.whisper_model",
        )
    else:
        print(f"{WARN}whisper.cpp 不可用（brew install whisper-cpp）")
    all_ok &= check(
        "至少一个转写后端可用", funasr_ok or whisper_ok,
        "FunASR（推荐，中文强）或 whisper.cpp 二选一装好",
    )

    # 6. 纪要模板与 DeepSeek key（可选）
    template = str(config.get("summary_template") or "meeting")
    all_ok &= check(
        "纪要模板有效",
        template in SUMMARY_TEMPLATES,
        f"summary_template 只能是：{' / '.join(SUMMARY_TEMPLATES)}",
    )
    prompt_file = str(config.get("summary_prompt_file") or "").strip()
    if prompt_file:
        all_ok &= check(
            "自定义提示词文件存在",
            resolve_path(prompt_file).is_file(),
            "检查 summary_prompt_file 路径，或留空使用内置模板",
        )
    load_dotenv()
    if bool(config.get("summary_enabled", True)):
        key_env = str(config.get("summary_api_key_env") or "DEEPSEEK_API_KEY")
        all_ok &= check(
            f"{key_env} 已配置", bool(os.environ.get(key_env, "").strip()),
            f"在项目根目录建 .env，写一行 {key_env}=...；"
            "不想用 LLM 就把 config 的 summary_enabled 改成 false",
        )
    else:
        print(f"{OK} 纪要已关闭（summary_enabled=false），跳过 API key 检查")

    print("\n== 结论 ==")
    if all_ok:
        if args.test_notification and notify_mode not in {"off", "none", "disabled"}:
            sent = notify_feishu(config, title="recording-inbox 通知测试")
            if not check("飞书测试消息发送成功", sent, "检查消息权限和通知配置"):
                return 1
        print(f"{OK} 环境就绪。跑一次试试：python3 scripts/run.py")
        return 0
    print(f"{FAIL} 还有缺项，按上面的提示逐条补齐后重跑本脚本。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
