"""Compatibility façade for the original ``record_bridge.py`` API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import DEFAULT_ENDPOINT, DEFAULT_MODEL
from .git_adapter import GitCommitter
from .organization import OpenAICompatibleOrganizer, parse_organization
from .pipeline import RecordPipeline
from .sources import (
    AUDIO_SUFFIXES,
    ATTACHMENT_SUFFIXES,
    IGNORED_NAMES,
    TEXT_SUFFIXES,
    RecordGroup,
    SourceScanner,
    source_signature,
)
from .state import StateStore
from .storage import RecordStore, extract_frontmatter, parse_ai_section, render_structured, safe_copy, yaml_value


DEFAULT_VOICE_MEMOS = (
    Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
DEFAULT_INBOX = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/AhaMomentInbox"
DEFAULT_VAULT = Path.home() / "Documents/Aha Moment Vault"
DEFAULT_PROXY_URL = DEFAULT_ENDPOINT


class _CallbackOrganizer:
    def __init__(self, bridge: "Bridge") -> None:
        self.bridge = bridge

    def organize(self, text: str) -> dict[str, Any]:
        return self.bridge._call_luna(text)


class Bridge:
    """Keep the prototype constructor while delegating to public adapters."""

    def __init__(
        self,
        vault: Path,
        sources: list[Path],
        state_path: Path | None = None,
        proxy_url: str = DEFAULT_PROXY_URL,
        model: str = DEFAULT_MODEL,
        mode: str = "collect-and-organize",
        auto_commit: bool = True,
        retry_ai: bool = False,
        dry_run: bool = False,
        after_epoch: float | None = None,
    ) -> None:
        self.vault = Path(vault).expanduser().resolve()
        self.sources = [Path(path).expanduser().resolve() for path in sources]
        self.state_path = (state_path or self.vault / ".bridge/state.json").expanduser().resolve()
        self.proxy_url = proxy_url.rstrip("/")
        self.model = model
        self.mode = mode
        self.auto_commit = auto_commit
        self.retry_ai = retry_ai
        self.dry_run = dry_run
        self.after_epoch = after_epoch
        self.state_store = StateStore(self.state_path)
        self.state = self.state_store.data
        self._http_organizer = OpenAICompatibleOrganizer(
            self.proxy_url,
            self.model,
            api_key=os.environ.get("AHA_API_KEY"),
        )
        self.store = RecordStore(self.vault)
        self.committer = GitCommitter(self.vault)
        self.pipeline = RecordPipeline(
            SourceScanner(self.sources, after_epoch=after_epoch),
            self.store,
            _CallbackOrganizer(self),
            self.state_store,
            committer=self.committer,
            mode=self.mode,
            auto_commit=self.auto_commit,
            retry_ai=self.retry_ai,
            dry_run=self.dry_run,
        )

    def _call_luna(self, text: str) -> dict[str, Any]:
        return self._http_organizer.organize(text).as_dict()

    def _record_path(self, group: RecordGroup) -> Path:
        return self.store.record_path(group)

    def _group_signature(self, group: RecordGroup) -> str:
        return source_signature(group)

    def _raw_content(self, group: RecordGroup) -> tuple[str, str]:
        return self.store.raw_content(group)

    def _copy_sources(self, group: RecordGroup) -> None:
        self.store.copy_sources(group)

    def _load_state(self) -> dict[str, Any]:
        return self.state_store.data

    def _save_state(self) -> None:
        if not self.dry_run:
            self.state_store.save()

    def _render_record(
        self,
        group: RecordGroup,
        signature: str,
        existing: str | None,
        ai_status: str,
        ai_error: str | None = None,
        processing_mode: str | None = None,
    ) -> str:
        return self.store.render_raw(
            group,
            signature,
            existing,
            ai_status=ai_status,
            ai_error=ai_error,
            processing_mode=processing_mode or self.mode,
        )

    def _write_ai_section(self, record_path: Path, result: dict[str, Any]) -> None:
        self.store.update_organization(record_path, result)

    def _commit(self, record_path: Path, record_id: str) -> str | None:
        if not self.auto_commit or self.dry_run:
            return None
        return self.committer.commit(record_path, record_id, self.state_path)

    def process_group(self, group: RecordGroup) -> dict[str, Any]:
        return self.pipeline.process(group)

    def scan(self) -> list[dict[str, Any]]:
        results = self.pipeline.scan()
        self.state = self.state_store.data
        return results

    def watch(self, interval: float) -> None:
        self.pipeline.watch(interval)


def source_groups(roots: list[Path], after_epoch: float | None = None) -> list[RecordGroup]:
    return SourceScanner(roots, after_epoch=after_epoch).scan()


def parse_json_response(content: str) -> dict[str, Any]:
    return parse_organization(content).as_dict()
