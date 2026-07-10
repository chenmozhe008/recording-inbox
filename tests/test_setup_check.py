from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("setup_check_module", ROOT / "scripts" / "setup_check.py")
assert SPEC and SPEC.loader
setup_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_check)


class SetupCheckTests(unittest.TestCase):
    def test_missing_config_stops_with_one_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_root = setup_check.ROOT
            setup_check.ROOT = Path(tmp)
            output = io.StringIO()
            try:
                with contextlib.redirect_stdout(output):
                    result = setup_check.main([])
            finally:
                setup_check.ROOT = original_root

        text = output.getvalue()
        self.assertEqual(result, 1)
        self.assertIn("python scripts/setup.py", text)
        self.assertNotIn("lark-cli 已安装", text)
        self.assertNotIn("DEEPSEEK_API_KEY", text)


if __name__ == "__main__":
    unittest.main()
