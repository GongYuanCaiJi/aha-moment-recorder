from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "prototype/record-bridge"))
from record_bridge import Bridge, source_groups  # noqa: E402


class FakeBridge(Bridge):
    calls = 0

    def _call_luna(self, text: str):  # type: ignore[no-untyped-def]
        type(self).calls += 1
        self.last_text = text
        return {
            "classification": "想法",
            "topic": ["測試流程"],
            "structured_output": "把原始內容整理成可讀段落。",
            "summary": "測試記錄已完成整理。",
        }


class RecordBridgeTests(unittest.TestCase):
    def test_one_record_keeps_audio_text_transcript_and_is_idempotent(self):
        FakeBridge.calls = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            audio = inbox / "20260802 120000-TEST1234.m4a"
            audio.write_bytes(b"fake-audio")
            (inbox / "20260802 120000-TEST1234.txt").write_text(
                "這是原始文字。", encoding="utf-8"
            )
            (inbox / "20260802 120000-TEST1234.transcript.txt").write_text(
                "這是逐字稿。", encoding="utf-8"
            )

            bridge = FakeBridge(vault=vault, sources=[inbox], auto_commit=False)
            first = bridge.scan()
            self.assertEqual(first[0]["status"], "completed")
            record = vault / "records/vm-20260802-120000-test1234/record.md"
            self.assertTrue(record.is_file())
            content = record.read_text(encoding="utf-8")
            self.assertIn("![[attachments/raw-audio.m4a]]", content)
            self.assertIn("這是原始文字。", content)
            self.assertIn("這是逐字稿。", content)
            self.assertEqual(content.count("## AI 整理"), 1)
            self.assertEqual(content.count("### 分類"), 1)
            self.assertTrue((record.parent / "attachments/raw-audio.m4a").is_file())

            second = bridge.scan()
            self.assertEqual(second[0]["status"], "unchanged")
            self.assertEqual(FakeBridge.calls, 1)

    def test_later_transcript_updates_same_record_without_overwriting_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            audio = inbox / "idea.m4a"
            audio.write_bytes(b"fake-audio")

            bridge = FakeBridge(vault=vault, sources=[inbox], mode="collect-and-organize", auto_commit=False)
            pending = bridge.scan()
            self.assertEqual(pending[0]["status"], "pending")
            record = vault / "records/vm-idea/record.md"
            self.assertIn("等待逐字稿", record.read_text(encoding="utf-8"))

            (inbox / "idea.transcript.txt").write_text("補上的逐字稿。", encoding="utf-8")
            completed = bridge.scan()
            self.assertEqual(completed[0]["status"], "completed")
            content = record.read_text(encoding="utf-8")
            self.assertIn("補上的逐字稿。", content)
            self.assertIn("原始音訊", content)
            self.assertIn("狀態：已完成", content)
            self.assertEqual(content.count("## AI 整理"), 1)

    def test_capture_only_never_calls_ai(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "note.md").write_text("只收錄內容。", encoding="utf-8")
            FakeBridge.calls = 0
            bridge = FakeBridge(vault=vault, sources=[inbox], mode="capture-only", auto_commit=False)
            result = bridge.scan()
            self.assertEqual(result[0]["status"], "skipped")
            self.assertEqual(FakeBridge.calls, 0)
            content = next((vault / "records").rglob("record.md")).read_text(encoding="utf-8")
            self.assertIn("只收錄（未啟用 AI 整理）", content)

    def test_record_level_mode_can_be_switched_later(self):
        FakeBridge.calls = 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "mode.md").write_text("可稍後整理的原始文字。", encoding="utf-8")
            bridge = FakeBridge(vault=vault, sources=[inbox], mode="capture-only", auto_commit=False)
            self.assertEqual(bridge.scan()[0]["status"], "skipped")
            record = next((vault / "records").rglob("record.md"))
            content = record.read_text(encoding="utf-8").replace(
                'processing_mode: "capture-only"',
                'processing_mode: "collect-and-organize"',
            )
            record.write_text(content, encoding="utf-8")
            result = bridge.scan()[0]
            self.assertEqual(result["status"], "completed")
            self.assertEqual(FakeBridge.calls, 1)
            self.assertIn('processing_mode: "collect-and-organize"', record.read_text(encoding="utf-8"))

    def test_state_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "note.txt").write_text("狀態測試。", encoding="utf-8")
            FakeBridge(vault=vault, sources=[inbox], auto_commit=False).scan()
            state = json.loads((vault / ".bridge/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["version"], 1)
            self.assertEqual(len(state["groups"]), 1)


if __name__ == "__main__":
    unittest.main()
