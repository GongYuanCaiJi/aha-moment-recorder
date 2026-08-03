from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

from aha_moment_recorder import (
    OpenAICompatibleOrganizer,
    RecordPipeline,
    RecordStore,
    Settings,
    SourceScanner,
    StateStore,
    pipeline_from_settings,
)


class FakeOpenAITransport:
    """Deterministic OpenAI-compatible boundary for the isolated E2E fixture."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.fail_markers: set[str] = set()

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> Mapping[str, Any]:
        messages = payload["messages"]
        user_content = messages[1]["content"]
        self.requests.append(
            {
                "url": url,
                "payload": dict(payload),
                "headers": dict(headers),
                "timeout": timeout,
                "content": user_content,
            }
        )
        if any(marker in user_content for marker in self.fail_markers):
            raise OSError("synthetic HTTP 503 from fake transport")
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "classification": "file-backed fixture",
                                "topic": ["Issue 20"],
                                "structured_output": {
                                    "preserved": True,
                                    "source_count": 1,
                                },
                                "summary": "fake transport organization",
                            },
                            ensure_ascii=False,
                        )
                    }
                }
            ]
        }


class FakeGitRunner:
    def __init__(self, root: Path, *, commit_failures: int = 0) -> None:
        self.root = root.resolve()
        self.commit_failures = commit_failures
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        if args[-2:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args, 0, stdout=str(self.root) + "\n", stderr="")
        if args[-3:] == ["rev-parse", "--verify", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")
        if "commit" in args:
            if self.commit_failures:
                self.commit_failures -= 1
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="synthetic commit failure")
            return subprocess.CompletedProcess(args, 0, stdout="[fixture abc123] record\n", stderr="")
        if "status" in args:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="A  records/fixture/record.md\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class FakeTranscriber:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def transcribe(self, audio_path: Path, output_path: Path) -> str:
        self.calls.append((audio_path, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("自然語音的逐字稿。", encoding="utf-8")
        return "自然語音的逐字稿。"


class FileBackedEndToEndTests(unittest.TestCase):
    @staticmethod
    def _settings(root: Path, inbox: Path, vault: Path, *, mode: str, auto_commit: bool = True) -> Settings:
        return Settings(
            vault=vault,
            sources=(inbox,),
            state_path=vault / ".bridge" / "state.json",
            endpoint="https://fake.example/v1",
            model="fixture-model",
            mode=mode,
            auto_commit=auto_commit,
            api_key="fixture-key",
        )

    def test_isolated_inbox_vault_exercises_the_complete_public_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            audio = b"real fixture audio bytes\x00\x01"
            attachment = b"real fixture attachment bytes"
            raw_text = "原始 Markdown 必須永遠保留。"
            (inbox / "meeting.m4a").write_bytes(audio)
            (inbox / "meeting.md").write_text(raw_text, encoding="utf-8")
            (inbox / "meeting.pdf").write_bytes(attachment)

            transport = FakeOpenAITransport()
            git_runner = FakeGitRunner(vault, commit_failures=1)
            settings = self._settings(root, inbox, vault, mode="collect-and-organize")
            pipeline = pipeline_from_settings(
                settings,
                transport=transport,
                git_runner=git_runner,
                clock=lambda: "2026-08-02T00:00:00+00:00",
            )

            first = pipeline.scan()
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["status"], "error")
            self.assertIn("git commit failed", first[0]["error"])
            record_path = Path(first[0]["path"])
            self.assertTrue(record_path.is_file())
            record_dir = record_path.parent
            self.assertEqual((record_dir / "attachments" / "raw-audio.m4a").read_bytes(), audio)
            self.assertEqual((record_dir / "attachments" / "raw-text-01.md").read_text(encoding="utf-8"), raw_text)
            self.assertEqual(
                (record_dir / "attachments" / "attachment-meeting.pdf").read_bytes(),
                attachment,
            )
            content = record_path.read_text(encoding="utf-8")
            self.assertIn(raw_text, content)
            self.assertIn('source_status: "preserved"', content)
            self.assertIn('ai_status: "completed"', content)
            self.assertEqual(len(transport.requests), 1)

            state = json.loads((vault / ".bridge" / "state.json").read_text(encoding="utf-8"))
            self.assertTrue(state["groups"][first[0]["record_id"]]["commit_pending"])

            retried = pipeline.scan()
            self.assertEqual(retried[0]["status"], "completed")
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(len([call for call in git_runner.calls if "commit" in call]), 2)

            unchanged = pipeline.scan()
            self.assertEqual(unchanged[0]["status"], "unchanged")
            self.assertEqual(len(transport.requests), 1)

            transcript = "後到的逐字稿也要追加，而不是覆蓋原始來源。"
            (inbox / "meeting.transcript.txt").write_text(transcript, encoding="utf-8")
            with_transcript = pipeline.scan()[0]
            self.assertEqual(with_transcript["status"], "completed")
            self.assertTrue(with_transcript["transcript"])
            self.assertEqual(len(transport.requests), 2)
            updated = record_path.read_text(encoding="utf-8")
            self.assertIn(raw_text, updated)
            self.assertIn(transcript, updated)
            self.assertEqual(
                (record_dir / "attachments" / "transcript-01.txt").read_text(encoding="utf-8"),
                transcript,
            )
            self.assertEqual(updated.count("## AI 整理"), 1)

            capture_source = inbox / "capture.md"
            capture_source.write_text("先只收錄這筆內容。", encoding="utf-8")
            capture_pipeline = pipeline_from_settings(
                self._settings(root, inbox, vault, mode="capture-only"),
                transport=transport,
                git_runner=git_runner,
                clock=lambda: "2026-08-02T00:00:00+00:00",
            )
            capture_result = next(
                result for result in capture_pipeline.scan() if result["record_id"] != with_transcript["record_id"]
            )
            self.assertEqual(capture_result["status"], "skipped")
            self.assertEqual(len(transport.requests), 2)
            capture_record = Path(capture_result["path"])
            capture_content = capture_record.read_text(encoding="utf-8")
            self.assertIn('processing_mode: "capture-only"', capture_content)
            self.assertNotIn("### 分類", capture_content)

            capture_record.write_text(
                capture_content.replace(
                    'processing_mode: "capture-only"',
                    'processing_mode: "collect-and-organize"',
                    1,
                ),
                encoding="utf-8",
            )
            switched_pipeline = pipeline_from_settings(
                self._settings(root, inbox, vault, mode="collect-and-organize"),
                transport=transport,
                git_runner=git_runner,
                clock=lambda: "2026-08-02T00:00:00+00:00",
            )
            switched = next(
                result
                for result in switched_pipeline.scan()
                if result["record_id"] == capture_result["record_id"]
            )
            self.assertEqual(switched["status"], "completed")
            self.assertEqual(len(transport.requests), 3)
            self.assertIn("### 分類", capture_record.read_text(encoding="utf-8"))

            error_source = inbox / "error.md"
            error_source.write_text("AI-ERROR: synthetic provider failure", encoding="utf-8")
            transport.fail_markers.add("AI-ERROR")
            error_pipeline = pipeline_from_settings(
                self._settings(root, inbox, vault, mode="collect-and-organize"),
                transport=transport,
                git_runner=git_runner,
                clock=lambda: "2026-08-02T00:00:00+00:00",
            )
            error_result = next(
                result
                for result in error_pipeline.scan()
                if result["record_id"] == "note-error"
            )
            self.assertEqual(error_result["status"], "error")
            self.assertIn("synthetic HTTP 503", error_result["error"])
            self.assertIn(
                'ai_status: "error"',
                Path(error_result["path"]).read_text(encoding="utf-8"),
            )
            self.assertEqual(len(transport.requests), 4)

    def test_natural_text_and_audio_inputs_route_to_separate_records_without_sidecars(self) -> None:
        """A human can type and speak independently; neither input needs a paired filename."""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "voice-20260804-1234.m4a").write_bytes(b"audio from a human capture")
            (inbox / "thought-20260804-1234.txt").write_text(
                "文字輸入應該進入自己的記錄。", encoding="utf-8"
            )

            transport = FakeOpenAITransport()
            transcriber = FakeTranscriber()
            organizer = OpenAICompatibleOrganizer(
                "https://fake.example/v1",
                "fixture-model",
                api_key="fixture-key",
                transport=transport,
            )
            pipeline = RecordPipeline(
                SourceScanner([inbox]),
                RecordStore(vault),
                organizer,
                StateStore(vault / ".bridge" / "state.json"),
                auto_commit=False,
                transcriber=transcriber,
            )

            first = pipeline.scan()

            self.assertEqual(
                {item["record_id"] for item in first},
                {"vm-voice-20260804-1234", "note-thought-20260804-1234"},
            )
            self.assertTrue(all(item["status"] == "completed" for item in first))
            self.assertEqual(len(transport.requests), 2)
            self.assertEqual(len(transcriber.calls), 1)

            voice_record = vault / "records/vm-voice-20260804-1234/record.md"
            text_record = vault / "records/note-thought-20260804-1234/record.md"
            voice_content = voice_record.read_text(encoding="utf-8")
            text_content = text_record.read_text(encoding="utf-8")
            self.assertIn("### 原始音訊", voice_content)
            self.assertIn("自然語音的逐字稿。", voice_content)
            self.assertIn("### 分類", voice_content)
            self.assertIn("文字輸入應該進入自己的記錄。", text_content)
            self.assertIn("### 分類", text_content)
            self.assertNotIn("### 原始音訊", text_content)

            second = pipeline.scan()
            self.assertTrue(all(item["status"] == "unchanged" for item in second))
            self.assertEqual(len(transport.requests), 2)
            self.assertEqual(len(transcriber.calls), 1)


if __name__ == "__main__":
    unittest.main()
