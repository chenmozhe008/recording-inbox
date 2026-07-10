from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402


class CommonTests(unittest.TestCase):
    def test_folder_link_is_converted_to_token(self) -> None:
        self.assertEqual(
            common.folder_token_from("https://example.feishu.cn/drive/folder/FldbExample?from=home"),
            "FldbExample",
        )

    def test_current_user_open_id_is_detected(self) -> None:
        payload = {
            "identities": {
                "user": {"available": True, "openId": "ou_test_user"},
            },
        }
        with patch.object(common, "lark_auth_status", return_value=payload):
            self.assertEqual(common.current_user_open_id({}), "ou_test_user")

    def test_direct_notification_uses_lark_cli_and_document_link(self) -> None:
        captured: list[str] = []

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            captured.extend(command)
            return subprocess.CompletedProcess(command, 0, "{}", "")

        config = {
            "feishu_notify_mode": "direct",
            "feishu_notify_user_id": "ou_test_user",
            "executables": {"lark_cli": "lark-cli"},
        }
        with patch.object(common, "run_command", side_effect=fake_run):
            sent = common.notify_feishu(
                config,
                title="项目短会",
                doc_result={"data": {"url": "https://example.feishu.cn/docx/demo"}},
            )
        self.assertTrue(sent)
        self.assertIn("+messages-send", captured)
        self.assertIn("ou_test_user", captured)
        markdown = captured[captured.index("--markdown") + 1]
        self.assertIn("打开飞书纪要", markdown)
        self.assertIn("https://example.feishu.cn/docx/demo", markdown)

    def test_legacy_webhook_config_remains_supported(self) -> None:
        config = {"feishu_notify_webhook": "https://example.invalid/hook"}
        with patch.object(common, "_send_webhook_notification", return_value=True) as sender:
            self.assertTrue(common.notify_feishu(config, title="旧配置"))
        sender.assert_called_once()

    def test_disabled_notification_is_already_handled(self) -> None:
        self.assertTrue(common.notify_feishu({"feishu_notify_mode": "off"}, title="测试"))


if __name__ == "__main__":
    unittest.main()
