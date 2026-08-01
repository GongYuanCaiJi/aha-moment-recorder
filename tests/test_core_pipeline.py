from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from aha_moment_recorder.config import ConfigError, load_settings
from aha_moment_recorder.git_adapter import GitCommitError, GitCommitter
from aha_moment_recorder.organization import (
    OrganizationError,
    OpenAICompatibleOrganizer,
    parse_organization,
)
from aha_moment_recorder.pipeline import RecordPipeline
from aha_moment_recorder.sources import RecordGroup, SourceScanner
from aha_moment_recorder.state import StateStore
from aha_moment_recorder.storage import RecordStore


class FakeOrganizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def organize(self, text: str) -> dict[str, object]:
        self.calls.append(text)
        return {
            "classification": "想法",
            "topic": ["核心流程"],
            "structured_output": {"內容": ["保留來源", "追加整理"]},
            "summary": "測試記錄已完成整理。",
        }


class FailingOrganizer:
    def organize(self, text: str) -> dict[str, object]:
        raise AssertionError("capture-only must not call the organizer")


class FailingThenSuccessfulCommitter:
    def __init__(self) -> None:
        self.calls = 0

    def commit(self, record_path: Path, record_id: str, state_path: Path) -> str:
        self.calls += 1
        if self.calls == 1:
            raise GitCommitError("synthetic commit failure")
        return "synthetic commit"


class RecordingTransport:
    def __init__(self) -> None:
        self.url = ""
        self.payload: dict[str, object] = {}
        self.headers: dict[str, str] = {}
        self.timeout = 0.0

    def post(self, url: str, payload: dict[str, object], headers: dict[str, str], timeout: float):
        self.url = url
        self.payload = payload
        self.headers = headers
        self.timeout = timeout
        return {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"classification":"想法","topic":"測試","structured_output":{"a":1},"summary":"摘要"}\n```'
                    }
                }
            ]
        }


class RecordingGitRunner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[-2:] == ["rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(args, 0, stdout=str(self.root) + "\n", stderr="")
        if "status" in args:
            return subprocess.CompletedProcess(args, 0, stdout="A  records/note-fixture/record.md\n", stderr="")
        if "commit" in args:
            return subprocess.CompletedProcess(args, 0, stdout="[main abc123] record\n", stderr="")
        if args[-2:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args, 0, stdout="abc123\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class CorePipelineTests(unittest.TestCase):
    def test_source_scanner_keeps_transcript_only_and_attachments(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            inbox = Path(temp) / "inbox"
            inbox.mkdir()
            (inbox / "voice.m4a").write_bytes(b"audio")
            (inbox / "voice.txt").write_text("原始文字", encoding="utf-8")
            (inbox / "voice.transcript.markdown").write_text("逐字稿", encoding="utf-8")
            (inbox / "voice.pdf").write_bytes(b"pdf")
            (inbox / "unknown.bin").write_bytes(b"ignore")
            (inbox / "later.transcript.md").write_text("只有逐字稿", encoding="utf-8")

            groups = SourceScanner([inbox]).scan()
            voice = next(group for group in groups if group.key == "voice")
            later = next(group for group in groups if group.key == "later")
            self.assertEqual([path.name for path in voice.raw_text], ["voice.txt"])
            self.assertEqual([path.name for path in voice.transcript], ["voice.transcript.markdown"])
            self.assertEqual([path.name for path in voice.attachments], ["voice.pdf"])
            self.assertEqual(later.source_type, "transcript")
            self.assertEqual([path.name for path in later.transcript], ["later.transcript.md"])
            self.assertNotIn("unknown.bin", {path.name for group in groups for path in group.all_sources})

    def test_configuration_precedence_and_secret_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "settings.toml"
            config.write_text(
                """
[record_bridge]
vault = "config-vault"
sources = ["config-inbox"]
state = "config-state.json"
endpoint = "http://config/v1"
model = "config-model"
mode = "capture-only"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            env = {
                "AHA_VAULT": str(root / "env-vault"),
                "AHA_SOURCES": str(root / "env-inbox"),
                "AHA_ENDPOINT": "http://env/v1",
                "AHA_MODEL": "env-model",
                "AHA_API_KEY": "fixture-key",
            }
            settings = load_settings(
                config,
                env=env,
                cli={
                    "vault": root / "cli-vault",
                    "sources": [root / "cli-inbox"],
                    "model": "cli-model",
                    "mode": "collect-and-organize",
                },
                cwd=root,
            )
            self.assertEqual(settings.vault, (root / "cli-vault").resolve())
            self.assertEqual(settings.sources, ((root / "cli-inbox").resolve(),))
            self.assertEqual(settings.state_path, (root / "config-state.json").resolve())
            self.assertEqual(settings.endpoint, "http://env/v1")
            self.assertEqual(settings.model, "cli-model")
            self.assertEqual(settings.mode, "collect-and-organize")
            self.assertEqual(settings.api_key, "fixture-key")

            config.write_text('api_key = "must-not-be-in-toml"\n', encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_settings(config, env={}, cwd=root)

    def test_organization_is_strict_and_http_is_injectable(self) -> None:
        result = parse_organization(
            'prefix\n```json\n{"classification":"想法","topic":["測試"],"structured_output":{"nested":[1]},"summary":"摘要"}\n```\nsuffix'
        )
        self.assertEqual(result.as_dict()["topic"], ["測試"])
        self.assertEqual(result.as_dict()["structured_output"], {"nested": [1]})
        self.assertEqual(
            parse_organization(
                {
                    "classification": "紀錄",
                    "topic": [],
                    "structured_output": "內容",
                    "summary": "摘要",
                }
            ).as_dict()["topic"],
            [],
        )
        for value in (
            {"classification": "x", "topic": "t", "structured_output": "s"},
            {
                "classification": "x",
                "topic": "t",
                "structured_output": "s",
                "summary": "ok",
                "extra": "no",
            },
            {"classification": "", "topic": "t", "structured_output": "s", "summary": "ok"},
        ):
            with self.assertRaises(OrganizationError):
                parse_organization(value)

        transport = RecordingTransport()
        organizer = OpenAICompatibleOrganizer(
            "https://provider.example/v1",
            "test-model",
            api_key_provider=lambda: "fixture-key",
            reasoning_effort="low",
            timeout=3,
            transport=transport,
        )
        self.assertEqual(organizer.organize("內容").classification, "想法")
        self.assertEqual(transport.url, "https://provider.example/v1/chat/completions")
        self.assertEqual(transport.headers["Authorization"], "Bearer fixture-key")
        self.assertEqual(transport.payload["model"], "test-model")
        self.assertEqual(transport.timeout, 3)

    def test_pipeline_preserves_sources_and_capture_only_skips_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            source = inbox / "note.txt"
            source.write_text("不可覆寫的原始資訊", encoding="utf-8")
            (inbox / "note.pdf").write_bytes(b"attachment")

            store = RecordStore(vault, clock=lambda: "2026-08-02T00:00:00+00:00")
            state = StateStore(vault / ".bridge/state.json", clock=lambda: "2026-08-02T00:00:00+00:00")
            pipeline = RecordPipeline(
                SourceScanner([inbox]),
                store,
                FailingOrganizer(),
                state,
                mode="capture-only",
                auto_commit=False,
            )
            result = pipeline.scan()
            self.assertEqual(result[0]["status"], "skipped")
            record = vault / "records/note-note/record.md"
            self.assertIn("不可覆寫的原始資訊", record.read_text(encoding="utf-8"))
            self.assertTrue((record.parent / "attachments/raw-text-01.txt").is_file())
            self.assertTrue((record.parent / "attachments/attachment-note.pdf").is_file())
            self.assertEqual(source.read_text(encoding="utf-8"), "不可覆寫的原始資訊")
            self.assertNotIn("### 分類", record.read_text(encoding="utf-8"))

    def test_pipeline_organizes_transcript_only_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "only.transcript.md").write_text("只有逐字稿內容", encoding="utf-8")
            organizer = FakeOrganizer()
            state = StateStore(vault / ".bridge/state.json", clock=lambda: "2026-08-02T00:00:00+00:00")
            pipeline = RecordPipeline(
                SourceScanner([inbox]),
                RecordStore(vault, clock=lambda: "2026-08-02T00:00:00+00:00"),
                organizer,
                state,
                auto_commit=False,
            )
            first = pipeline.scan()
            second = pipeline.scan()
            self.assertEqual(first[0]["status"], "completed")
            self.assertEqual(second[0]["status"], "unchanged")
            self.assertEqual(len(organizer.calls), 1)
            content = (vault / "records/note-only/record.md").read_text(encoding="utf-8")
            self.assertIn("只有逐字稿內容", content)
            self.assertNotIn("### 原始文字", content)
            self.assertEqual(content.count("## AI 整理"), 1)

    def test_commit_failure_is_reported_and_next_scan_retries_without_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            (inbox / "retry.txt").write_text("可重試內容", encoding="utf-8")
            organizer = FakeOrganizer()
            committer = FailingThenSuccessfulCommitter()
            state = StateStore(vault / ".bridge/state.json", clock=lambda: "2026-08-02T00:00:00+00:00")
            pipeline = RecordPipeline(
                SourceScanner([inbox]),
                RecordStore(vault, clock=lambda: "2026-08-02T00:00:00+00:00"),
                organizer,
                state,
                committer=committer,  # type: ignore[arg-type]
                auto_commit=True,
            )
            first = pipeline.scan()[0]
            self.assertEqual(first["status"], "error")
            self.assertEqual(len(organizer.calls), 1)
            persisted = json.loads((vault / ".bridge/state.json").read_text(encoding="utf-8"))
            self.assertTrue(persisted["groups"]["note-retry"]["commit_pending"])

            second = pipeline.scan()[0]
            self.assertEqual(second["status"], "completed")
            self.assertEqual(len(organizer.calls), 1)
            self.assertFalse(state.get("note-retry")["commit_pending"])

    def test_git_committer_limits_commit_to_record_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            vault = Path(temp) / "vault"
            vault.mkdir()
            record = vault / "records/note-fixture/record.md"
            state = vault / ".bridge/state.json"
            record.parent.mkdir(parents=True)
            state.parent.mkdir(parents=True)
            record.write_text("record", encoding="utf-8")
            state.write_text("{}", encoding="utf-8")
            runner = RecordingGitRunner(vault)

            commit = GitCommitter(vault, runner=runner).commit(record, "note-fixture", state)
            self.assertTrue(commit)
            add = next(call for call in runner.calls if "add" in call)
            commit_call = next(call for call in runner.calls if "commit" in call)
            self.assertEqual(add[add.index("--") + 1 :], ["records/note-fixture", ".bridge/state.json"])
            self.assertIn("--only", commit_call)
            self.assertEqual(
                commit_call[commit_call.index("--") + 1 :],
                ["records/note-fixture", ".bridge/state.json"],
            )
            self.assertEqual(commit, "abc123")


if __name__ == "__main__":
    unittest.main()
