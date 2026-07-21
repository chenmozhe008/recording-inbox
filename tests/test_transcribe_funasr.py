from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "transcribe_funasr_module",
    ROOT / "scripts" / "transcribe_funasr.py",
)
assert SPEC and SPEC.loader
transcribe_funasr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transcribe_funasr)


class TranscribeFunASRTests(unittest.TestCase):
    def test_clean_text_preserves_terminal_chinese_punctuation(self) -> None:
        self.assertEqual(
            transcribe_funasr.clean_text("今天确认方案，明天开始执行。"),
            "今天确认方案，明天开始执行。",
        )

    def test_clean_text_removes_leading_noise_but_not_final_question_mark(self) -> None:
        self.assertEqual(
            transcribe_funasr.clean_text(" . ，这个方案什么时候确认？"),
            "这个方案什么时候确认？",
        )

    def test_clean_text_removes_sensevoice_tags_and_collapses_repeats(self) -> None:
        self.assertEqual(
            transcribe_funasr.clean_text("<|zh|><|NEUTRAL|>测试测试测试。"),
            "测试。",
        )


if __name__ == "__main__":
    unittest.main()
