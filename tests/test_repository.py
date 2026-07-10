from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
