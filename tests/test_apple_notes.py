from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aha_moment_recorder.apple_notes import AppleNotesScanner
from aha_moment_recorder.organization import Organization
from aha_moment_recorder.pipeline import RecordPipeline
from aha_moment_recorder.sources import source_signature
from aha_moment_recorder.state import StateStore
from aha_moment_recorder.storage import RecordStore


class FakeFolder:
    def __init__(self, name: str) -> None:
        self.name = name


class FakeAttachment:
    def __init__(self, filename: str, *, audio: bool = False, available: bool = True) -> None:
        self.filename = filename
        self.file_extension = Path(filename).suffix.lstrip(".")
        self.type_uti = "com.apple.m4a-audio" if audio else "public.data"
        self.is_audio = audio
        self.available = available

    def save_attachment(self, destination: Path, **_: object) -> bool:
        if not self.available:
            return False
        destination.write_bytes(b"fake attachment")
        return True


class FakeNote:
    def __init__(self, uuid: str, title: str, content: str, folder: str = "Notes") -> None:
        self.uuid = uuid
        self.note_id = 1
        self.id = 1
        self.title = title
        self.content = content
        self.folder = FakeFolder(folder)
        self.creation_date = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.modification_date = datetime(2026, 8, 2, tzinfo=timezone.utc)
        self.attachments: list[FakeAttachment] = []


class FakeParser:
    notes: list[FakeNote] = []

    def __init__(self, _: str) -> None:
        pass

    def load_data(self) -> None:
        return None


class FakeOrganizer:
    def organize(self, _: str) -> Organization:
        return Organization("想法", ("Apple Notes",), "結構化內容", "摘要")


class AppleNotesTests(unittest.TestCase):
    def test_scanner_preserves_note_metadata_and_skips_recently_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "NoteStore.sqlite"
            database.write_bytes(b"fixture")
            active = FakeNote("A-1", "一則備忘錄", "原始備忘錄內容")
            active.attachments = [FakeAttachment("voice.m4a", audio=True), FakeAttachment("photo.bin")]
            deleted = FakeNote("A-2", "已刪除", "不應匯入", folder="Recently Deleted")
            FakeParser.notes = [active, deleted]

            scanner = AppleNotesScanner(database, root / "staging", parser_factory=FakeParser)
            groups = scanner.scan()

            self.assertEqual(len(groups), 1)
            group = groups[0]
            self.assertEqual(group.title, "一則備忘錄")
            self.assertEqual(group.source_type, "apple-note")
            self.assertEqual(group.captured_at, "2026-08-02T00:00:00+00:00")
            self.assertEqual(len(group.audio), 1)
            self.assertEqual(len(group.attachments), 1)
            self.assertEqual(group.raw_text[0].read_text(encoding="utf-8"), "原始備忘錄內容")

    def test_scanned_note_runs_through_the_same_record_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "NoteStore.sqlite"
            database.write_bytes(b"fixture")
            note = FakeNote("A-3", "可整理備忘錄", "保留這段原文")
            note.attachments = [FakeAttachment("missing.m4a", audio=True, available=False)]
            FakeParser.notes = [note]
            scanner = AppleNotesScanner(database, root / "staging", parser_factory=FakeParser)
            vault = root / "vault"
            pipeline = RecordPipeline(
                scanner,
                RecordStore(vault),
                FakeOrganizer(),
                StateStore(vault / ".bridge/state.json"),
                auto_commit=False,
            )

            result = pipeline.scan()[0]
            self.assertEqual(result["status"], "completed")
            record = Path(result["path"])
            content = record.read_text(encoding="utf-8")
            self.assertIn("保留這段原文", content)
            self.assertIn("missing.m4a", content)
            self.assertIn("### 分類", content)
            self.assertTrue(source_signature(scanner.scan()[0]))


if __name__ == "__main__":
    unittest.main()
