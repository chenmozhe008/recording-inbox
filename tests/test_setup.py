from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("setup_wizard", ROOT / "scripts" / "setup.py")
assert SPEC and SPEC.loader
setup_wizard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_wizard)


class SetupTests(unittest.TestCase):
    def test_existing_executable_config_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.example.json").write_text(json.dumps({
                "summary_enabled": True,
                "executables": {"lark_cli": "lark-cli", "ffmpeg": "ffmpeg"},
            }), encoding="utf-8")
            original_root = setup_wizard.ROOT
            setup_wizard.ROOT = root
            try:
                merged = setup_wizard.merged_config({
                    "executables": {"lark_cli": "C:/tools/lark-cli.cmd"},
                })
            finally:
                setup_wizard.ROOT = original_root
        self.assertEqual(merged["executables"]["lark_cli"], "C:/tools/lark-cli.cmd")
        self.assertEqual(merged["executables"]["ffmpeg"], "ffmpeg")

    def test_api_key_is_written_without_echo_or_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_root = setup_wizard.ROOT
            setup_wizard.ROOT = root
            try:
                setup_wizard.write_env_key("first")
                setup_wizard.write_env_key("second")
                content = (root / ".env").read_text(encoding="utf-8")
            finally:
                setup_wizard.ROOT = original_root
        self.assertEqual(content, "DEEPSEEK_API_KEY=second\n")


if __name__ == "__main__":
    unittest.main()
