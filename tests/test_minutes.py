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

    def test_summary_speaker_aliases_are_consistent_and_protect_source_sections(self) -> None:
        summary = """# 项目讨论

## 智能纪要
说话人2提出方案。

## 主题大纲
- 说话人1表示同意，发言人2方负责推进。

## 待办
- [ ] speaker_2整理资料，speaker_1确认。

## 智能章节
### [00:00:00] 方案讨论
说话人1回应说话人2。

## 金句时刻
> 说话人2：先把原型跑通。
"""

        cleaned = minutes.neutralize_summary_speaker_numbers(summary)

        self.assertIn("一方提出方案", cleaned)
        self.assertIn("另一方表示同意，一方负责推进", cleaned)
        self.assertIn("一方整理资料，另一方确认", cleaned)
        self.assertIn("说话人1回应说话人2", cleaned)
        self.assertIn("说话人2：先把原型跑通", cleaned)
        self.assertNotIn("一方方", cleaned)

    def test_single_summary_alias_uses_neutral_phrase(self) -> None:
        summary = "# 记录\n\n## 智能纪要\n说话人3提出先做测试。\n"
        self.assertIn(
            "有发言人提出先做测试",
            minutes.neutralize_summary_speaker_numbers(summary),
        )


if __name__ == "__main__":
    unittest.main()
