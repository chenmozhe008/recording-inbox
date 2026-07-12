from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import minutes  # noqa: E402
from common import SUMMARY_TEMPLATES  # noqa: E402


class MinutesTests(unittest.TestCase):
    def test_each_builtin_template_is_loadable(self) -> None:
        for template in SUMMARY_TEMPLATES:
            with self.subTest(template=template):
                prompt = minutes.build_prompt(
                    {"title": "测试"},
                    "[00:00:00] 测试内容",
                    {"summary_template": template},
                )
                self.assertIn("本次文稿类型要求", prompt)
                self.assertGreater(len(prompt), 500)

    def test_custom_prompt_file_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp) / "custom.md"
            custom.write_text("重点提取行业术语和明确风险。", encoding="utf-8")
            prompt = minutes.build_prompt(
                {"title": "测试"},
                "[00:00:00] 测试内容",
                {"summary_prompt_file": str(custom)},
            )
        self.assertIn("重点提取行业术语和明确风险", prompt)

    def test_single_speaker_labels_are_removed(self) -> None:
        transcript = "[00:00:00] 说话人1：今天讨论方案。"
        summary = "说话人1：建议先做测试。发言人1：随后发布。"
        cleaned = minutes.suppress_single_speaker_labels(summary, transcript)
        self.assertNotIn("说话人1", cleaned)
        self.assertNotIn("发言人1", cleaned)

    def test_multiple_speaker_labels_are_kept(self) -> None:
        transcript = "说话人1：方案一。\n说话人2：同意。"
        summary = "说话人1：提出方案；说话人2：表示同意。"
        self.assertEqual(minutes.suppress_single_speaker_labels(summary, transcript), summary)


if __name__ == "__main__":
    unittest.main()
