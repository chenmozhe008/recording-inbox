#!/usr/bin/env python3
"""智能纪要：把逐字稿交给 LLM（默认 DeepSeek，任何 OpenAI 兼容接口都行）生成 Markdown 纪要。

- API key 放项目根目录 .env 的 DEEPSEEK_API_KEY（永不入 git）；
- config.summary_enabled = false 时跳过纪要，只保留逐字稿；
- 输出直接要 Markdown 而不是 JSON——省去 schema 校验，读者好改提示词。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from common import log, update_status

PROMPT_TEMPLATE = """你是一名会议纪要整理助手。下面是一段录音的逐字稿（可能有转写错误，请按上下文纠正后再理解）。

请输出 Markdown 格式的纪要，结构如下：
## 概要
（两三句话说清这段录音在讲什么）
## 要点
（列点，每点一句话，按主题分组）
## 待办
（如果录音里出现了明确的行动项就列出来，没有就写「无」）

要求：用中文；忠于原文不要脑补；标点用中文符号。

录音标题：{title}
逐字稿：
{transcript}
"""


def call_llm(prompt: str, config: dict[str, Any]) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY（写在项目根目录 .env 里）")
    base_url = str(config.get("summary_api_base", "https://api.deepseek.com")).rstrip("/")
    model = str(config.get("summary_model", "deepseek-chat"))
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_error: Exception | None = None
    for _attempt in range(2):  # 网络抖动重试一次；4xx 直接抛
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = str(payload["choices"][0]["message"]["content"]).strip()
            if content:
                return content
            last_error = RuntimeError("模型返回空内容")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if 400 <= exc.code < 500:
                raise RuntimeError(f"模型接口返回 {exc.code}（多半是 key 或余额问题）：{detail}") from exc
            last_error = RuntimeError(f"模型接口返回 {exc.code}：{detail}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError) as exc:
            last_error = exc
    raise RuntimeError(f"纪要生成失败：{last_error}")


def generate_minutes(task_dir: Path, config: dict[str, Any]) -> bool:
    manifest = json.loads((task_dir / "manifest.json").read_text(encoding="utf-8"))
    transcript = (task_dir / "transcript.txt").read_text(encoding="utf-8")

    if not bool(config.get("summary_enabled", True)):
        # 不要纪要：直接把逐字稿包装成产物
        (task_dir / "minutes.md").write_text(
            f"# {manifest['title']}\n\n## 逐字稿\n\n{transcript}", encoding="utf-8",
        )
        update_status(task_dir, "minutes_ready", "纪要已跳过（summary_enabled=false），仅逐字稿。")
        return True

    update_status(task_dir, "summarizing", "正在生成智能纪要。")
    try:
        summary = call_llm(
            PROMPT_TEMPLATE.format(title=manifest["title"], transcript=transcript),
            config,
        )
    except Exception as exc:
        update_status(task_dir, "minutes_failed", str(exc)[:300], error=str(exc)[:800])
        return False

    (task_dir / "minutes.md").write_text(
        f"# {manifest['title']}\n\n{summary}\n\n---\n\n## 逐字稿\n\n{transcript}",
        encoding="utf-8",
    )
    update_status(task_dir, "minutes_ready", "纪要已生成。")
    return True


if __name__ == "__main__":
    import sys

    from common import load_config, resolve_path

    if len(sys.argv) != 2:
        raise SystemExit("用法：python3 scripts/minutes.py <任务包目录>")
    ok = generate_minutes(resolve_path(sys.argv[1]), load_config())
    log("纪要完成" if ok else "纪要失败")
