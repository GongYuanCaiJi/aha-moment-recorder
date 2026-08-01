from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping

import aha_moment_recorder as public
from aha_moment_recorder import (
    ConfigError,
    Organization,
    OrganizationError,
    OpenAICompatibleOrganizer,
    RecordStore,
    SourceScanner,
    StateStore,
    load_settings,
    parse_organization,
    source_signature,
)


class FakeTransport:
    def __init__(self, response: Mapping[str, Any] | str) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> Mapping[str, Any] | str:
        self.calls.append(
            {
                "url": url,
                "payload": dict(payload),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        return self.response


class PublicInterfaceContractTests(unittest.TestCase):
    def test_top_level_exports_are_the_supported_contract(self) -> None:
        expected = {
            "ConfigError",
            "GitCommitError",
            "GitCommitter",
            "Organization",
            "OrganizationError",
            "OpenAICompatibleOrganizer",
            "RecordGroup",
            "RecordPipeline",
            "RecordStore",
            "Settings",
            "SourceMetadata",
            "SourceScanner",
            "StateStore",
            "load_settings",
            "parse_organization",
            "pipeline_from_settings",
            "source_signature",
        }
        self.assertTrue(expected.issubset(set(public.__all__)))
        for name in expected:
            self.assertTrue(callable(getattr(public, name)), name)

    def test_file_sources_and_record_store_preserve_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "inbox"
            vault = root / "vault"
            inbox.mkdir()
            audio = b"fixture-audio-bytes"
            attachment = b"fixture-pdf-bytes"
            (inbox / "moment.m4a").write_bytes(audio)
            (inbox / "moment.md").write_text("不可覆寫的原始文字", encoding="utf-8")
            (inbox / "moment.transcript.txt").write_text("原始逐字稿", encoding="utf-8")
            (inbox / "moment.pdf").write_bytes(attachment)
            (inbox / "ignored.bin").write_bytes(b"not a supported source")

            group = SourceScanner([inbox]).scan()[0]
            self.assertEqual(group.record_id, "vm-moment")
            self.assertEqual([path.name for path in group.raw_text], ["moment.md"])
            self.assertEqual([path.name for path in group.transcript], ["moment.transcript.txt"])
            self.assertEqual([path.name for path in group.attachments], ["moment.pdf"])
            self.assertNotIn(inbox / "ignored.bin", group.all_sources)

            signature = source_signature(group)
            store = RecordStore(vault, clock=lambda: "2026-08-02T00:00:00+00:00")
            destinations = store.copy_sources(group)
            destination_by_name = {path.name: name for path, name in destinations.items()}
            record_path = store.write_record(
                group,
                signature,
                ai_status="completed",
                processing_mode="collect-and-organize",
            )
            store.update_organization(
                record_path,
                Organization(
                    classification="想法",
                    topic=("測試", "保留來源"),
                    structured_output={"nested": ["value"]},
                    summary="摘要",
                ),
            )

            content = record_path.read_text(encoding="utf-8")
            self.assertIn("不可覆寫的原始文字", content)
            self.assertIn("原始逐字稿", content)
            self.assertIn("source_status: \"preserved\"", content)
            self.assertEqual(content.count("## AI 整理"), 1)
            self.assertEqual(
                (record_path.parent / "attachments" / destination_by_name["moment.m4a"]).read_bytes(),
                audio,
            )
            self.assertEqual(
                (record_path.parent / "attachments" / destination_by_name["moment.pdf"]).read_bytes(),
                attachment,
            )
            self.assertEqual(
                (inbox / "moment.md").read_text(encoding="utf-8"),
                "不可覆寫的原始文字",
            )

    def test_state_store_recovers_invalid_json_and_round_trips_public_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_path = Path(temp) / ".bridge" / "state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text("{invalid", encoding="utf-8")

            state = StateStore(state_path, clock=lambda: "2026-08-02T00:00:00+00:00")
            self.assertIsNone(state.get("missing"))
            state.set("note-1", {"status": "completed", "nested": {"value": 1}})
            snapshot = state.snapshot()
            state.set("note-2", {"status": "skipped"})
            state.restore(snapshot)
            state.remove("missing")
            state.save()

            reloaded = StateStore(state_path)
            self.assertEqual(reloaded.get("note-1"), {"status": "completed", "nested": {"value": 1}})
            self.assertIsNone(reloaded.get("note-2"))

    def test_organizer_uses_openai_compatible_transport_and_rejects_bad_json(self) -> None:
        transport = FakeTransport(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '```json\n{"classification":"想法","topic":["測試"],'
                                '"structured_output":{"nested":[1]},"summary":"摘要"}\n```'
                            )
                        }
                    }
                ]
            }
        )
        organizer = OpenAICompatibleOrganizer(
            "https://provider.example/v1",
            "fixture-model",
            api_key="fixture-key",
            reasoning_effort="low",
            timeout=3,
            transport=transport,
        )

        result = organizer.organize("來源內容")
        request = transport.calls[0]
        self.assertEqual(result.as_dict()["structured_output"], {"nested": [1]})
        self.assertEqual(request["url"], "https://provider.example/v1/chat/completions")
        self.assertEqual(request["payload"]["model"], "fixture-model")
        self.assertEqual(request["payload"]["reasoning_effort"], "low")
        self.assertEqual(request["headers"]["Authorization"], "Bearer fixture-key")
        self.assertIn("來源內容", request["payload"]["messages"][1]["content"])
        self.assertEqual(request["timeout"], 3)

        no_key_transport = FakeTransport(
            {
                "choices": [
                    {"message": {"content": json.dumps({
                        "classification": "紀錄",
                        "topic": [],
                        "structured_output": "內容",
                        "summary": "摘要",
                    })}}
                ]
            }
        )
        OpenAICompatibleOrganizer(
            "https://provider.example/v1",
            "fixture-model",
            transport=no_key_transport,
        ).organize("沒有 key 仍可測試")
        self.assertNotIn("Authorization", no_key_transport.calls[0]["headers"])

        with self.assertRaises(OrganizationError):
            OpenAICompatibleOrganizer(
                "https://provider.example/v1",
                "fixture-model",
                transport=FakeTransport("not-json"),
            ).organize("錯誤 JSON")

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

    def test_config_precedence_secret_boundary_and_cli_doctor_failure(self) -> None:
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
            settings = load_settings(
                config,
                env={
                    "AHA_VAULT": str(root / "env-vault"),
                    "AHA_SOURCES": str(root / "env-inbox"),
                    "AHA_ENDPOINT": "http://env/v1",
                    "AHA_MODEL": "env-model",
                },
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
            self.assertIsNone(settings.api_key)

            config.write_text('api_key = "secret-in-toml"\n', encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_settings(config, env={}, cwd=root)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "aha_moment_recorder",
                    "doctor",
                    "--vault",
                    str(root / "missing-vault"),
                    "--source",
                    str(root / "missing-inbox"),
                    "--state",
                    str(root / "state.json"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            diagnostic = json.loads(completed.stdout)
            self.assertFalse(diagnostic["vault"]["exists"])
            self.assertFalse(diagnostic["sources"][0]["exists"])
            self.assertEqual(diagnostic["api_key"], "not configured")
            self.assertNotIn("secret-in-toml", completed.stdout + completed.stderr)

            help_result = subprocess.run(
                [sys.executable, "-m", "aha_moment_recorder", "--help"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(help_result.returncode, 0)
            self.assertIn("doctor", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
