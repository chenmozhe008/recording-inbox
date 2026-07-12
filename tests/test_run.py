from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import common  # noqa: E402
import minutes  # noqa: E402
import run  # noqa: E402


class RunTests(unittest.TestCase):
    def test_dead_process_lock_is_cleared_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "run.lock"
            lock.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
            with patch.object(run, "_pid_is_running", return_value=False):
                self.assertTrue(run.acquire_run_lock(lock, fallback_max_age=999999))
            self.assertEqual(run._lock_pid(lock), os.getpid())
            run.release_run_lock(lock)
            self.assertFalse(lock.exists())

    def test_live_process_lock_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / "run.lock"
            lock.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
            self.assertFalse(run.acquire_run_lock(lock, fallback_max_age=1))
            self.assertTrue(lock.exists())

    def test_published_task_retries_only_notification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp)
            common.atomic_write_json(task / "manifest.json", {"title": "测试"})
            common.atomic_write_json(task / "status.json", {
                "status": "published",
                "message": "处理完成。",
                "notification_sent": False,
                "local_output": "/tmp/demo.md",
                "feishu_import": {"url": "https://example.feishu.cn/docx/demo"},
            })
            with patch.object(run, "notify_feishu", return_value=True) as notify:
                run.retry_pending_notification(task, {})
            notify.assert_called_once()
            status = common.read_status(task)
            self.assertTrue(status["notification_sent"])
            self.assertEqual(status["status"], "published")

    def test_simulated_pipeline_reaches_published(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            task = base / "data" / "tasks" / "demo"
            task.mkdir(parents=True)
            (task / "audio.m4a").write_bytes(b"fake-audio")
            common.atomic_write_json(task / "manifest.json", {
                "id": "demo",
                "title": "20260710 录音-1200",
                "audio_file": "audio.m4a",
            })
            common.update_status(task, "pending", "等待转写。")

            config = {
                "work_dir": str(base / "data"),
                "output_dir": str(base / "output"),
                "summary_enabled": True,
                "summary_template": "meeting",
                "summary_api_key_env": "TEST_SUMMARY_KEY",
                "feishu_notify_mode": "direct",
            }

            def fake_transcribe(task_dir: Path, _config: dict) -> bool:
                (task_dir / "transcript.txt").write_text(
                    "[00:00:00] 今天讨论场地确认和剪辑反馈。",
                    encoding="utf-8",
                )
                common.update_status(task_dir, "transcript_ready", "转写完成。")
                return True

            summary = (
                "# 拍摄场地与剪辑反馈\n\n"
                "## 智能纪要\n讨论了场地确认和剪辑反馈。\n\n"
                "## 待办\n- [ ] 周三前确认场地。\n"
            )
            with patch.object(run, "pull", return_value=0), \
                 patch.object(run, "transcribe_task", side_effect=fake_transcribe), \
                 patch.object(minutes, "call_llm", return_value=summary), \
                 patch.object(run, "notify_feishu", return_value=True), \
                 patch.dict(os.environ, {"TEST_SUMMARY_KEY": "test-key"}):
                run.run_once(config)

            status = common.read_status(task)
            self.assertEqual(status["status"], "published")
            self.assertTrue(status["notification_sent"])
            self.assertEqual(status["display_title"], "拍摄场地与剪辑反馈")
            outputs = list((base / "output").glob("*.md"))
            self.assertEqual(len(outputs), 2)
            self.assertTrue(any("智能纪要" in path.name for path in outputs))
            self.assertTrue(any("文字稿" in path.name for path in outputs))

    def test_publish_creates_two_documents_and_links_minutes_to_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task"
            task.mkdir()
            common.atomic_write_json(task / "manifest.json", {"title": "项目短会"})
            (task / "minutes.md").write_text("# 项目短会\n\n## 智能纪要\n结论。", encoding="utf-8")
            (task / "transcript.txt").write_text("[00:00:00] 原始发言。", encoding="utf-8")
            imports = [
                {"data": {"url": "https://example.feishu.cn/docx/transcript"}},
                {"data": {"url": "https://example.feishu.cn/docx/minutes"}},
            ]
            with patch.object(run, "configured_folder", return_value="folder"), \
                 patch.object(run, "import_markdown_as_docx", side_effect=imports) as importer, \
                 patch.object(run, "notify_feishu", return_value=True) as notify:
                self.assertTrue(run.publish_task(task, {"output_dir": str(Path(tmp) / "output")}))
            self.assertEqual(importer.call_count, 2)
            self.assertIn("文字稿：项目短会", importer.call_args_list[0].args[2])
            published_minutes = task / "minutes-publish.md"
            self.assertIn("打开文字稿", published_minutes.read_text(encoding="utf-8"))
            notify.assert_called_once()
            self.assertEqual(
                notify.call_args.kwargs["transcript_doc_result"]["data"]["url"],
                "https://example.feishu.cn/docx/transcript",
            )


if __name__ == "__main__":
    unittest.main()
