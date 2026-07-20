from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("setup_check_module", ROOT / "scripts" / "setup_check.py")
assert SPEC and SPEC.loader
setup_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_check)


class SetupCheckTests(unittest.TestCase):
    def test_read_asr_versions_uses_configured_python(self) -> None:
        completed = mock.Mock(
            returncode=0,
            stdout='{"funasr": "1.3.10", "modelscope": "1.37.1", "torch": "2.8.0"}\n',
        )
        with mock.patch.object(setup_check, "run_quiet", return_value=completed) as run:
            versions = setup_check.read_asr_versions("custom-python")

        self.assertEqual(versions["funasr"], "1.3.10")
        self.assertEqual(versions["modelscope"], "1.37.1")
        self.assertEqual(run.call_args.args[0][0], "custom-python")

    def test_asr_baseline_is_exact_but_non_blocking_for_main(self) -> None:
        self.assertTrue(setup_check.asr_baseline_matches({
            "funasr": "1.3.10",
            "modelscope": "1.37.1",
        }))
        self.assertFalse(setup_check.asr_baseline_matches({
            "funasr": "1.3.22",
            "modelscope": "1.38.1",
        }))

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
