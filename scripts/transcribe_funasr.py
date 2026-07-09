#!/usr/bin/env python3
"""Run SenseVoice through FunASR and emit the shared transcript contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any

from workflow_common import collapse_repeats, to_simplified

# SenseVoice 原始输出带富文本标记，必须清洗成纯文本。注意这个版本的解码会把
# 标记拆成带空格形式（如 “< | en | >”“< | S pee ch | >”），rich_transcription_postprocess
# 只认 “<|en|>” 紧凑格式，所以这里用容忍空格的正则直接剥，更稳。
# 标记内容枚举：语言 zh/en/yue/ja/ko、情感 NEUTRAL/HAPPY/EMO_UNKNOWN…、
# 事件 Speech/BGM/Applause…、ITN withitn/woitn。
_SENSEVOICE_TAG = re.compile(r"<\s*\|.*?\|\s*>")
_TAG_LEFTOVER = re.compile(r"\b(withitn|woitn|EMO_UNKNOWN)\b", re.IGNORECASE)


def clean_text(text: str) -> str:
    """清洗 SenseVoice 富文本标记 + 修空格/重复标点，得到可读纯文本。"""
    raw = str(text or "")
    raw = _SENSEVOICE_TAG.sub("", raw)          # 剥 < | xx | > 标记（容忍空格）
    raw = _TAG_LEFTOVER.sub("", raw)            # 个别漏网的纯文字标记
    # 日文假名/韩文谚文在中文录音里只会是 SenseVoice 误判产生的乱码，直接删
    raw = re.sub(r"[぀-ヿㇰ-ㇿ가-힣]+", "", raw)
    # 中文之间 / 数字之间被插入的空格收掉（“202 6”→“2026”）
    raw = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", raw)
    raw = re.sub(r"(?<=\d)\s+(?=\d)", "", raw)
    # 混合/重复中文标点归一：“，。”→“。”、“？，”→“？”、“，，”→“，”
    raw = re.sub(r"[，、]+(?=[。！？])", "", raw)
    raw = re.sub(r"(?<=[。！？])[，、]+", "", raw)
    raw = re.sub(r"([，。！？、；：])\1+", r"\1", raw)
    raw = re.sub(r"\s+\.\s+", " ", raw)         # 孤立英文句点噪声 “ . ”
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    # 去掉行首残留的孤立英文碎片/标点（如剥标记后留下的 “ . ”“Yeah .”）
    raw = raw.strip(" .，,。")
    raw = collapse_repeats(raw)                 # 折叠复读幻觉
    raw = to_simplified(raw)                    # 统一简体
    return raw.strip()


def timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


class DiarizationTimeout(RuntimeError):
    """Raised when local speaker clustering takes too long."""


def diarize(chunks, sr, *, speaker_model: str = "iic/speech_campplus_sv_zh-cn_16k-common",
            min_dur: float = 0.6, distance_threshold: float = 0.8,
            min_cluster_dur: float = 3.0, timeout_seconds: int = 0):
    """学飞书妙记思路做本地说话人分离：给每个 VAD 语音段提 campplus 声纹向量，
    再按余弦距离层次聚类成「说话人 1/2/3…」。**只分编号、不认名字**（飞书也只到编号）。
    刻意绕开 FunASR 集成的 distribute_spk（历史上在单人/短段会崩），改自己提 embedding + 聚类。

    返回与 chunks 等长的 1-based 说话人编号列表；任何环节失败或只有一段时回落全 1，
    保证不阻断转写主流程。"""
    n = len(chunks)
    if n <= 1:
        return [1] * n
    def _timeout(signum: int, frame: Any) -> None:  # noqa: ARG001
        raise DiarizationTimeout("说话人分离超时，退回单说话人")

    old_handler: Any = None
    if timeout_seconds > 0:
        old_handler = signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(timeout_seconds)
    try:
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering
        from modelscope.pipelines import pipeline as ms_pipeline
        from modelscope.utils.constant import Tasks
        # disable_update=True 关掉 modelscope 每次构建时的在线更新检查——
        # 否则慢网下会卡死（实测下载期撞网会无限等待）。模型已缓存时纯离线加载。
        sv = ms_pipeline(
            task=Tasks.speaker_verification,
            model=speaker_model,
            disable_update=True,
        )

        # 批量提声纹：一次喂多段比逐段快几十倍（实测 5 段 0.1s）。太短的段声纹不稳，跳过、稍后随邻。
        min_len = int(min_dur * sr)
        embs: list[Any] = [None] * n
        ok_rows: list[int] = []
        batch_idx: list[int] = []
        batch_audio: list[Any] = []

        def _flush() -> None:
            if not batch_audio:
                return
            try:
                out = sv(list(batch_audio), output_emb=True)
                arr = (
                    np.asarray(out["embs"])
                    if isinstance(out, dict) and out.get("embs") is not None
                    else None
                )
            except Exception as exc:
                sys.stderr.write(f"[diarize] 批量提声纹失败一批：{exc}\n")
                arr = None
            if arr is not None and len(arr) == len(batch_idx):
                for k, i in enumerate(batch_idx):
                    embs[i] = arr[k]
                    ok_rows.append(i)
            batch_idx.clear()
            batch_audio.clear()

        for i, ch in enumerate(chunks):
            if len(ch) < min_len:
                continue
            batch_idx.append(i)
            batch_audio.append(np.asarray(ch, dtype="float32"))
            if len(batch_audio) >= 64:
                _flush()
        _flush()

        if len(ok_rows) <= 1:
            return [1] * n

        mat = np.vstack([np.asarray(embs[i], dtype="float64") for i in ok_rows])
        mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)
        labels = AgglomerativeClustering(
            n_clusters=None, metric="cosine", linkage="average",
            distance_threshold=distance_threshold,
        ).fit_predict(mat)
    except Exception as exc:  # 缺库/模型下不动/聚类超时 → 不分离，退回全 1
        sys.stderr.write(f"[diarize] 失败或超时，退回单说话人：{exc}\n")
        return [1] * n
    finally:
        if timeout_seconds > 0:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

    # 关键收敛步：声纹聚类会把短段/噪声段裂成很多碎类（实测 2 人电话裂成 30+ 类）。
    # 按「每个类的总说话时长」把不足 min_cluster_dur 秒的小碎类，并到余弦最近的大类质心，
    # 把说话人数收敛到合理范围（实测 2 人→2、嘈杂多人→3，优于飞书对同片的 11）。
    durs = np.array([len(chunks[i]) / sr for i in ok_rows])
    uniq = list(dict.fromkeys(labels.tolist()))
    cent: dict[int, Any] = {}
    for c in uniq:
        v = mat[labels == c].mean(0)
        cent[c] = v / (np.linalg.norm(v) + 1e-8)
    big = [c for c in uniq if float(durs[labels == c].sum()) >= min_cluster_dur]
    if big:
        remap = {
            c: (c if c in big else max(big, key=lambda b: float(np.dot(cent[c], cent[b]))))
            for c in uniq
        }
        labels = np.array([remap[c] for c in labels])

    # 有声纹的段先填（合并后的）聚类结果；空段（太短跳过的）继承时间上最近的前一段
    raw: list[int | None] = [None] * n
    for row, i in enumerate(ok_rows):
        raw[i] = int(labels[row])
    last = None
    for i in range(n):
        if raw[i] is None:
            raw[i] = last if last is not None else int(labels[0])
        last = raw[i]

    # 按首次出现顺序把 cluster id 重排成稳定的 1,2,3…（飞书风格）
    order: dict[int, int] = {}
    for c in raw:
        if c not in order:
            order[c] = len(order) + 1
    return [order[c] for c in raw]


def normalized_segments(result: dict[str, Any]) -> list[dict[str, Any]]:
    sentence_info = result.get("sentence_info") or []
    segments: list[dict[str, Any]] = []
    speaker_order: dict[str, int] = {}
    for index, sentence in enumerate(sentence_info, start=1):
        start_ms = float(sentence.get("start", 0))
        end_ms = float(sentence.get("end", start_ms))
        text = clean_text(sentence.get("text") or sentence.get("sentence", ""))
        if not text:
            continue
        speaker = sentence.get("spk")
        speaker_label = "speaker_1"
        if speaker is not None:
            raw_speaker = str(speaker)
            if raw_speaker not in speaker_order:
                speaker_order[raw_speaker] = len(speaker_order) + 1
            speaker_label = f"speaker_{speaker_order[raw_speaker]}"
        segments.append({
            "id": index,
            "start": start_ms / 1000,
            "end": end_ms / 1000,
            "speaker": speaker_label,
            "text": text,
        })
    if segments:
        return segments

    text = clean_text(result.get("text", ""))
    return [{
        "id": 1,
        "start": 0,
        "end": 0,
        "speaker": "speaker_1",
        "text": text,
    }] if text else []


def render_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"[{timestamp(float(item['start']))}] {str(item['speaker']).replace('speaker_', '说话人')}：{item['text']}"
        for item in segments
    ) + "\n"


def official_sensevoice_segments(args: argparse.Namespace, audio_path: str) -> list[dict[str, Any]]:
    """Use current FunASR/SenseVoice integrated VAD + ASR + punctuation + speaker labels.

    Keep this close to the official quick-start shape. In FunASR 1.3.10,
    adding punc_model + merge_vad here can trigger timestamp/punctuation length
    mismatches on real recordings; the minimal VAD + spk_model path returns
    sentence_info with `spk` and `sentence`.
    """
    from funasr import AutoModel

    model = AutoModel(
        model=args.model,
        trust_remote_code=True,
        vad_model=args.vad_model,
        spk_model=args.speaker_model,
        disable_update=True,
    )
    result = model.generate(
        input=audio_path,
        language=args.language,
        use_itn=True,
    )
    if not result:
        return []
    return normalized_segments(result[0])


def manual_sensevoice_segments(args: argparse.Namespace, audio_path: str, wav_path: str) -> list[dict[str, Any]]:
    """Fallback implementation: explicit VAD chunks + ASR + local speaker clustering."""
    from funasr import AutoModel
    import soundfile as sf

    vad = AutoModel(model=args.vad_model, trust_remote_code=True, disable_update=True)
    vad_out = vad.generate(input=wav_path)
    vad_segments = (vad_out[0] if vad_out else {}).get("value") or []

    asr = AutoModel(
        model=args.model,
        punc_model=args.punc_model,
        trust_remote_code=True,
        disable_update=True,
    )
    data, sr = sf.read(wav_path, dtype="float32")
    if getattr(data, "ndim", 1) > 1:
        data = data.mean(axis=1)

    segments: list[dict[str, Any]] = []
    spans = []
    chunks = []
    for s_ms, e_ms in vad_segments:
        a = max(0, int(s_ms / 1000 * sr))
        b = min(len(data), int(e_ms / 1000 * sr))
        if b > a:
            spans.append((s_ms, e_ms))
            chunks.append(data[a:b])
    if chunks:
        speaker_ids = diarize(
            chunks,
            sr,
            speaker_model=args.speaker_model,
            timeout_seconds=args.manual_diarization_timeout_seconds,
        )
        results = asr.generate(
            input=chunks,
            language=args.language,
            use_itn=True,
            batch_size_s=args.batch_size_s,
        )
        for idx, ((s_ms, e_ms), res, spk) in enumerate(
            zip(spans, results, speaker_ids), start=1
        ):
            text = clean_text(res.get("text", ""))
            if not text:
                continue
            segments.append({
                "id": idx,
                "start": s_ms / 1000,
                "end": e_ms / 1000,
                "speaker": f"speaker_{spk}",
                "text": text,
            })

    if not segments:
        res = asr.generate(input=wav_path, language=args.language, use_itn=True)
        text = clean_text(res[0].get("text", "")) if res else ""
        if text:
            segments = [{"id": 1, "start": 0, "end": 0, "speaker": "speaker_1", "text": text}]
    return segments


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe audio with FunASR SenseVoice.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", default="iic/SenseVoiceSmall")
    parser.add_argument("--vad-model", default="fsmn-vad")
    parser.add_argument("--punc-model", default="ct-punc")
    parser.add_argument("--speaker-model", default="cam++")
    parser.add_argument("--speaker-strategy", choices=["official", "manual"], default="official")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--batch-size-s", type=int, default=60)
    parser.add_argument("--merge-length-s", type=int, default=15)
    parser.add_argument("--max-single-segment-time-ms", type=int, default=30000)
    parser.add_argument("--manual-diarization-timeout-seconds", type=int, default=600)
    args = parser.parse_args()

    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise RuntimeError("当前 Python 环境未安装 funasr。") from exc
    import subprocess
    import tempfile

    audio_path = str(Path(args.audio).expanduser().resolve())
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # 统一转 16k 单声道 wav，便于按 VAD 时间戳精确切片
    wav_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
        check=True, capture_output=True,
    )

    segments: list[dict[str, Any]] = []
    if args.speaker_strategy == "official":
        try:
            segments = official_sensevoice_segments(args, audio_path)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[sensevoice] 官方说话人分离失败，回退手写聚类：{exc}\n")
    if not segments:
        segments = manual_sensevoice_segments(args, audio_path, wav_path)

    try:
        Path(wav_path).unlink(missing_ok=True)
    except OSError:
        pass

    payload = {
        "schema_version": 1,
        "backend": "funasr-sensevoice",
        "language": "auto",
        "segments": segments,
        "text": "\n".join(item["text"] for item in segments),
    }
    (output_dir / "transcript.txt").write_text(render_text(segments), encoding="utf-8")
    (output_dir / "transcript.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"backend": payload["backend"], "segments": len(segments)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
