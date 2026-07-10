#!/usr/bin/env python3
"""环境自检：一条条告诉你缺什么、怎么补。跑通它再跑主流程。

用法：python3 scripts/setup_check.py
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OK = "✅"
FAIL = "❌"
WARN = "⚠️ "


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


def main() -> int:
    print("== recording-inbox 环境自检 ==\n")
    print(f"系统：{platform.system()} {platform.release()}\n")
    all_ok = True

    # 1. 配置文件
    config_path = ROOT / "config.json"
    has_config = check(
        "config.json 存在", config_path.is_file(),
        "cp config.example.json config.json，然后按 README 填写",
    )
    all_ok &= has_config
    config: dict = {}
    if has_config:
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            all_ok &= check("config.json 是合法 JSON", False, f"JSON 语法错误：{exc}")
        inbox = str(config.get("feishu_inbox_folder_link") or config.get("feishu_inbox_folder_token") or "")
        all_ok &= check(
            "已填 feishu_inbox_folder_link（inbox 文件夹链接）", bool(inbox) and inbox.isascii(),
            "把飞书 inbox 文件夹链接贴进 config.json（见 docs/setup-feishu-app.md）",
        )

    # 2. lark-cli
    lark = str(config.get("executables", {}).get("lark_cli", "")) or "lark-cli"
    lark_found = shutil.which(lark) or Path(lark).expanduser().is_file()
    all_ok &= check(
        "lark-cli 已安装", bool(lark_found),
        "npm install -g @larksuite/cli（见 docs/setup-feishu-app.md）",
    )
    if lark_found:
        try:
            result = run_quiet([lark, "auth", "status"], timeout=30)
            all_ok &= check(
                "lark-cli 已登录授权", result.returncode == 0,
                "运行 lark-cli auth login --domain drive,docs 完成授权",
            )
        except (subprocess.SubprocessError, OSError):
            all_ok &= check("lark-cli 可执行", False, "检查安装是否完整")

    # 3. ffmpeg / ffprobe
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

    # 4. 转写后端：FunASR 或 whisper.cpp 至少一个
    funasr_py = str(config.get("executables", {}).get("funasr_python", "")) or "python3"
    funasr_ok = False
    try:
        funasr_ok = run_quiet([funasr_py, "-c", "import funasr"], timeout=60).returncode == 0
    except (subprocess.SubprocessError, OSError):
        pass
    whisper_bin = str(config.get("executables", {}).get("whisper_cpp", ""))
    whisper_ok = bool(
        (whisper_bin and Path(whisper_bin).expanduser().is_file())
        or shutil.which("whisper-cli")
    )
    if funasr_ok:
        print(f"{OK} FunASR 可用（主转写，中文效果好）")
    else:
        print(f"{WARN}FunASR 不可用（pip install funasr modelscope torch）")
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

    # 5. DeepSeek key（可选）
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DEEPSEEK_API_KEY=") :
                os.environ.setdefault("DEEPSEEK_API_KEY", line.split("=", 1)[1].strip())
    if bool(config.get("summary_enabled", True)):
        all_ok &= check(
            "DEEPSEEK_API_KEY 已配置", bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
            "在项目根目录建 .env，写一行 DEEPSEEK_API_KEY=sk-...；"
            "不想用 LLM 就把 config 的 summary_enabled 改成 false",
        )
    else:
        print(f"{OK} 纪要已关闭（summary_enabled=false），跳过 API key 检查")

    print("\n== 结论 ==")
    if all_ok:
        print(f"{OK} 环境就绪。跑一次试试：python3 scripts/run.py")
        return 0
    print(f"{FAIL} 还有缺项，按上面的提示逐条补齐后重跑本脚本。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
