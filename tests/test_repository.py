from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def tracked_files(self) -> list[Path]:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return [ROOT / line for line in result.stdout.splitlines() if line]

    def test_relative_markdown_links_exist(self) -> None:
        pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        missing: list[str] = []
        for path in self.tracked_files():
            if path.suffix.lower() != ".md":
                continue
            text = path.read_text(encoding="utf-8")
            for target in pattern.findall(text):
                target = target.split("#", 1)[0].strip().strip("<>")
                if not target or target.startswith(("http://", "https://", "mailto:", "../../")):
                    continue
                if not (path.parent / target).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [], "失效的 Markdown 链接：\n" + "\n".join(missing))

    def test_tracked_files_do_not_contain_secrets_or_local_paths(self) -> None:
        patterns = {
            "API key": re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
            "Feishu open_id": re.compile(r"ou_[A-Za-z0-9]{16,}"),
            "Feishu folder token": re.compile(r"Fld[A-Za-z0-9]{16,}"),
            "local user path": re.compile(r"/Users/" + "forwardyan/"),
        }
        findings: list[str] = []
        allowed_suffixes = {".py", ".md", ".json", ".yml", ".yaml", ".bat", ".plist"}
        for path in self.tracked_files():
            if path.suffix.lower() not in allowed_suffixes:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in patterns.items():
                if pattern.search(text):
                    findings.append(f"{label}: {path.relative_to(ROOT)}")
        self.assertEqual(findings, [], "发现疑似敏感信息：\n" + "\n".join(findings))

    def test_launchd_uses_project_python(self) -> None:
        text = (ROOT / "launchd" / "com.example.recording-inbox.plist").read_text(encoding="utf-8")
        self.assertIn("/path/to/recording-inbox/asr-venv/bin/python", text)
        self.assertNotIn("<string>/usr/bin/python3</string>", text)

    def test_public_discovery_entrypoints_are_consistent(self) -> None:
        required = [
            "README.md",
            "README.en.md",
            "llms.txt",
            "docs/llms.txt",
            "docs/index.md",
            "docs/faq.md",
            "docs/robots.txt",
            "docs/_config.yml",
            "docs/_includes/head-custom.html",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), f"缺少公开发现入口：{relative}")

        root_llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
        pages_llms = (ROOT / "docs" / "llms.txt").read_text(encoding="utf-8")
        self.assertEqual(root_llms, pages_llms, "仓库与项目页的 llms.txt 内容不一致")
        self.assertIn("Canonical project URL: https://github.com/chenmozhe008/recording-inbox", root_llms)
        self.assertNotRegex(root_llms, r"\]\((?!https://)[^)]+\)")

        public_text = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("README.md", "docs/index.md", "docs/faq.md", "llms.txt")
        )
        for phrase in ("AI 录音工作流", "录音转文字", "自动会议纪要", "本地转写", "FunASR"):
            self.assertIn(phrase, public_text, f"公开入口缺少核心检索语义：{phrase}")

        config = (ROOT / "docs" / "_config.yml").read_text(encoding="utf-8")
        self.assertIn("baseurl: /recording-inbox", config)
        self.assertIn("jekyll-seo-tag", config)
        self.assertIn("jekyll-sitemap", config)
        robots = (ROOT / "docs" / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("https://chenmozhe008.github.io/recording-inbox/sitemap.xml", robots)

        promotion = (ROOT / "docs" / "promotion-kit.md").read_text(encoding="utf-8")
        for public_submission in (
            "https://github.com/GitHubDaily/GitHubDaily/issues/937",
            "https://github.com/521xueweihan/HelloGitHub/issues/3431",
            "https://github.com/ruanyf/weekly/issues/10668",
        ):
            self.assertIn(public_submission, promotion, f"推广记录缺少公开投稿：{public_submission}")

    def test_structured_project_metadata_is_valid_json(self) -> None:
        head = (ROOT / "docs" / "_includes" / "head-custom.html").read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            head,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "缺少 JSON-LD 软件项目信息")
        payload = json.loads(match.group(1))
        self.assertEqual(payload["@type"], "SoftwareSourceCode")
        self.assertEqual(payload["codeRepository"], "https://github.com/chenmozhe008/recording-inbox")
        self.assertEqual(payload["softwareVersion"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
