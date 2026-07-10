from __future__ import annotations

import unittest
from unittest import mock

from scripts import pull_inbox


class PullInboxTests(unittest.TestCase):
    @mock.patch.object(pull_inbox, "drive_download")
    @mock.patch.object(pull_inbox, "drive_move")
    @mock.patch.object(pull_inbox, "create_folder", return_value="processed-token")
    @mock.patch.object(pull_inbox, "list_folder")
    @mock.patch.object(pull_inbox, "load_ledger", return_value={"already-seen"})
    @mock.patch.object(pull_inbox, "configured_folder", return_value="inbox-token")
    def test_seen_file_is_archived_without_redownload(
        self,
        _configured_folder: mock.Mock,
        _load_ledger: mock.Mock,
        list_folder: mock.Mock,
        _create_folder: mock.Mock,
        drive_move: mock.Mock,
        drive_download: mock.Mock,
    ) -> None:
        list_folder.return_value = [
            {"type": "file", "token": "already-seen", "name": "meeting.m4a"},
        ]

        config = {"supported_extensions": [".m4a"]}
        pulled = pull_inbox.pull(config)

        self.assertEqual(pulled, 0)
        drive_move.assert_called_once_with(config, "already-seen", "processed-token")
        drive_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
