#!/usr/bin/env python3
"""智能纪要：把逐字稿交给 LLM（默认 DeepSeek，任何 OpenAI 兼容接口都行）生成 Markdown 纪要。

- API key 放项目根目录 .env 的 DEEPSEEK_API_KEY（永不入 git）；
- config.summary_enabled = false 时跳过纪要，只保留逐字稿；
- 输出直接要 Markdown 而不是 JSON——省去 schema 校验，读者好改提示词。
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from common import atomic_write_json, log, resolve_path, update_status
from metrics import mark_stage_started, record_stage_finished

PROMPT_TEMPLATE = """你是中文会议纪要助手，请严格对标飞书妙记「智能纪要」的风格，但保持开源版轻量、可读。
只能根据输入内容总结，不要编造人物、日期、金额、链接、待办。

{speaker_policy}

本次文稿类型要求：
{template_instructions}

请输出 Markdown，结构必须如下：

# {{一句话内容标题}}

## 智能纪要
一段总览，概括整段录音围绕哪些事情展开，自然收束于「内容如下：」。

## 主题大纲
- **一级主题**
  - **子主题**：说明这一组内容。
    - 具体事实。保留原文里的数字、人名、机构、时间、专有名词和做法。
- **后续工作计划**
  - 只列录音结束后仍需要继续推进的事情；没有就写「无」。

## 待办
- [ ] 只列明确行动项，尽量写清负责人/对象/完成标准。
- 没有明确行动项就写「无」。

## 智能章节
按时间切 2-8 个章节。每章格式：
### [00:00:00] 章节标题
本章节用 2-4 句自然语言说明讨论了什么、结论是什么。

## 关键决策
没有明确决策就写「无」。有则按：
- **决策**：
- **背景问题**：
- **讨论方案**：
- **决策依据**：

## 金句时刻
无有信息量原话就写「无」。有则引用 1-3 句原话，并用一句话点评价值。

写作规则：
1. 标题是 8-20 字名词短语，必须从内容归纳，不要照抄「录音-时间」「测试录音」这类默认文件名，不要带日期。
2. 待办只收录录音结束后仍未完成、且原文有明确证据的行动；不要推断「添加微信、拉群、发资料」等原文没说的动作。
3. 对明显转写错误要按上下文纠正，例如 AIGC、DeepSeek、飞书、FunASR、SenseVoice、GitHub 等专名。
4. 单人录音不要写「说话人1」；多人讨论才可以用「说话人1/说话人2」区分观点。
5. 中文为主，夹杂英文术语时保留英文；标点用中文符号。

原始文件名/标题：{title}

逐字稿：
{transcript}
"""


def system_ssl_context() -> ssl.SSLContext:
    """优先使用系统证书库，兼容公司网络的受信任代理证书；绝不关闭 TLS 校验。"""
    try:
        import truststore  # type: ignore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def speaker_policy_text(transcript: str) -> str:
    speakers = set(re.findall(r"(?:说话人|speaker_)\s*([0-9]+)", transcript))
    if len(speakers) <= 1:
        return (
            "这是一段单人或近似单人录音。纪要、章节、待办里不要写「说话人1」"
            "或「speaker_1」，直接用自然叙述。"
        )
    return (
        "这是一段多人讨论。可以用「说话人1」「说话人2」区分观点，"
        "但不要出现 speaker_1 这类英文标签。"
    )


def template_instructions(config: dict[str, Any] | None = None) -> str:
    config = config or {}
    custom = str(config.get("summary_prompt_file") or "").strip()
    if custom:
        path = resolve_path(custom)
        if not path.is_file():
            raise RuntimeError(f"自定义提示词文件不存在：{path}")
    else:
        template = str(config.get("summary_template") or "meeting")
        path = resolve_path(f"prompts/{template}.md")
        if not path.is_file():
            raise RuntimeError(f"未知纪要模板：{template}")
    return path.read_text(encoding="utf-8").strip()


def build_prompt(
    manifest: dict[str, Any],
    transcript: str,
    config: dict[str, Any] | None = None,
) -> str:
    return PROMPT_TEMPLATE.format(
        title=str(manifest.get("title", "录音纪要")),
        transcript=transcript,
        speaker_policy=speaker_policy_text(transcript),
        template_instructions=template_instructions(config),
    )


def speaker_ids_in_text(text: str) -> set[str]:
    return set(re.findall(r"(?:说话人|发言人|speaker_)\s*([0-9]+)", text, re.IGNORECASE))


def suppress_single_speaker_labels(text: str, transcript: str) -> str:
    """Prompt 之外再兜底一次，避免单人录音偶发出现无意义编号。"""
    if len(speaker_ids_in_text(transcript)) > 1:
        return text
    return re.sub(
        r"(?:说话人|发言人|speaker_)\s*1\s*[：:]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )


def clean_generated_title(raw: str, fallback: str) -> str:
    title = raw.strip().strip("#").strip()
    title = re.sub(r"^(智能纪要|会议纪要|录音纪要|标题)\s*[：:]\s*", "", title).strip()
    title = re.sub(r"^\d{4}[-/.年]?\d{1,2}[-/.月]?\d{1,2}[日]?\s*", "", title).strip()
    title = re.sub(r"^录音[-_\s]*\d{4,}[-_\s]*\d{2,4}\s*", "", title).strip()
    if not title or len(title) < 4:
        return fallback
    return title[:30]


def extract_generated_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return clean_generated_title(stripped[2:], fallback)
        if stripped.startswith("标题：") or stripped.startswith("建议标题："):
            return clean_generated_title(stripped.split("：", 1)[1], fallback)
    return fallback


def ensure_h1(markdown: str, title: str) -> str:
    stripped = markdown.lstrip()
    if stripped.startswith("# "):
        return stripped
    return f"# {title}\n\n{stripped}"


def call_llm(prompt: str, config: dict[str, Any]) -> str:
    key_env = str(config.get("summary_api_key_env") or "DEEPSEEK_API_KEY")
    api_key = os.environ.get(key_env, "").strip()
    if not api_key:
        raise RuntimeError(f"缺少 {key_env}（写在项目根目录 .env 里）")
    base_url = str(config.get("summary_api_base", "https://api.deepseek.com")).rstrip("/")
    model = str(config.get("summary_model", "deepseek-v4-pro"))
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 7000,
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
            with urllib.request.urlopen(
                request,
                timeout=600,
                context=system_ssl_context(),
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = str(payload["choices"][0]["message"]["content"]).strip()
            if content:
                return content
            last_error = RuntimeError("模型返回空内容")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in {401, 403}:
                raise RuntimeError(f"模型 API Key 无效或没有权限（{exc.code}）：{detail}") from exc
            if exc.code in {402, 429}:
                raise RuntimeError(f"模型余额不足或请求受限（{exc.code}）：{detail}") from exc
            if 400 <= exc.code < 500:
                raise RuntimeError(f"模型请求配置有误（{exc.code}）：{detail}") from exc
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

    key_env = str(config.get("summary_api_key_env") or "DEEPSEEK_API_KEY")
    if not os.environ.get(key_env, "").strip():
        # 没配 key 不算失败——失败态会被 launchd 每 3 分钟重试，永远卡在这里。
        # 降级为只出文字记录，让闭环照样走完；想要智能纪要的用户看提示补 key 即可。
        (task_dir / "minutes.md").write_text(
            f"# {manifest['title']}\n\n"
            f"> 未配置 {key_env}（写在项目根目录 .env 里），"
            "本次只输出文字记录，没有智能纪要。\n\n"
            f"## 文字记录\n\n{transcript}",
            encoding="utf-8",
        )
        update_status(task_dir, "minutes_ready", "未配置 DEEPSEEK_API_KEY，已跳过智能纪要，仅输出文字记录。")
        return True

    update_status(task_dir, "summarizing", "正在生成智能纪要。")
    mark_stage_started(task_dir, "summary")
    try:
        summary = call_llm(
            build_prompt(manifest, transcript, config),
            config,
        )
    except Exception as exc:
        update_status(task_dir, "minutes_failed", str(exc)[:300], error=str(exc)[:800])
        return False

    fallback_title = str(manifest.get("title") or "录音纪要")
    generated_title = extract_generated_title(summary, fallback_title)
    if generated_title and generated_title != manifest.get("title"):
        manifest = {**manifest, "original_title": manifest.get("original_title") or manifest.get("title"), "title": generated_title}
        atomic_write_json(task_dir / "manifest.json", manifest)
    summary = ensure_h1(summary, generated_title)
    summary = suppress_single_speaker_labels(summary, transcript)
    # 文字稿由发布阶段单独生成、单独导入飞书；纪要文件只承载可快速阅读的内容。
    (task_dir / "minutes.md").write_text(summary, encoding="utf-8")
    update_status(task_dir, "minutes_ready", "智能纪要已生成。", display_title=generated_title)
    record_stage_finished(task_dir, config, "summary", backend=str(config.get("summary_model", "deepseek-v4-pro")))
    return True


if __name__ == "__main__":
    import sys

    from common import load_config, resolve_path

    if len(sys.argv) != 2:
        raise SystemExit("用法：python3 scripts/minutes.py <任务包目录>")
    ok = generate_minutes(resolve_path(sys.argv[1]), load_config())
    log("纪要完成" if ok else "纪要失败")
