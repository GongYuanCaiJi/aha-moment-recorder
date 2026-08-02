"""Public record processing pipeline and dependency assembly."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

from .apple_notes import AppleNotesScanner
from .config import CAPTURE_ONLY, COLLECT_AND_ORGANIZE, Settings, VALID_MODES, ProcessingMode
from .git_adapter import GitCommitError, GitCommitter, CommandRunner
from .organization import Organization, OrganizationError, OpenAICompatibleOrganizer, parse_organization
from .sources import CompositeScanner, MetadataReader, RecordGroup, Scanner, SourceScanner, source_signature
from .state import StateStore, utc_now
from .storage import RecordStore, extract_frontmatter


class Organizer(Protocol):
    def organize(self, text: str) -> Organization | Mapping[str, Any]: ...


class RecordPipeline:
    """Process normalized groups through storage, AI, state, and Git adapters."""

    def __init__(
        self,
        scanner: Scanner,
        store: RecordStore,
        organizer: Organizer | None,
        state: StateStore,
        *,
        committer: GitCommitter | None = None,
        mode: ProcessingMode = COLLECT_AND_ORGANIZE,
        auto_commit: bool = True,
        retry_ai: bool = False,
        dry_run: bool = False,
    ) -> None:
        self.scanner = scanner
        self.store = store
        self.organizer = organizer
        self.state = state
        self.committer = committer
        self.mode = mode
        self.auto_commit = auto_commit
        self.retry_ai = retry_ai
        self.dry_run = dry_run

    def process(self, group: RecordGroup) -> dict[str, Any]:
        try:
            signature = source_signature(group)
        except OSError as exc:
            # iCloud may expose a Voice Memo path before the file is fully
            # hydrated.  Leave state untouched so the next watch tick retries
            # instead of terminating the LaunchAgent.
            return {
                "record_id": group.record_id,
                "status": "deferred",
                "error": f"source is not ready: {str(exc)[:120]}",
            }
        previous = self.state.get(group.record_id)
        record_path = self.store.record_path(group)
        existing = self.store.read(group)
        existing_mode = extract_frontmatter(existing or "").get("processing_mode")
        effective_mode = existing_mode if existing_mode in VALID_MODES else self.mode

        if (
            previous
            and previous.get("commit_pending")
            and record_path.is_file()
            and previous.get("signature") == signature
            and previous.get("processing_mode", self.mode) == effective_mode
            and not self.retry_ai
        ):
            if self.committer is None or not self.auto_commit:
                return {
                    "record_id": group.record_id,
                    "status": "error",
                    "error": "record commit is still pending but Git is disabled",
                    "path": str(record_path),
                }
            try:
                commit = self.committer.commit(record_path, group.record_id, self.state.path)
            except (GitCommitError, OSError, RuntimeError) as exc:
                return {
                    "record_id": group.record_id,
                    "status": "error",
                    "error": str(exc)[:160],
                    "path": str(record_path),
                }
            pending_state = dict(previous)
            pending_state["commit_pending"] = False
            self.state.set(group.record_id, pending_state)
            self.state.save()
            return {
                "record_id": group.record_id,
                "status": previous.get("status", "completed"),
                "commit": commit,
                "path": str(record_path),
            }

        if (
            previous
            and record_path.is_file()
            and previous.get("signature") == signature
            and previous.get("processing_mode", self.mode) == effective_mode
            and previous.get("status") != "error"
            and not self.retry_ai
            and not previous.get("commit_pending")
        ):
            return {"record_id": group.record_id, "status": "unchanged"}

        try:
            if not self.dry_run:
                self.store.copy_sources(group)
            raw_text, transcript = self.store.raw_content(group)
        except OSError as exc:
            return {
                "record_id": group.record_id,
                "status": "deferred",
                "error": f"source changed while reading: {str(exc)[:120]}",
            }
        ai_status = "skipped" if effective_mode == CAPTURE_ONLY else "pending"
        ai_error: str | None = None
        organization: Organization | None = None

        if effective_mode != CAPTURE_ONLY and (raw_text or transcript):
            if not self.dry_run:
                if self.organizer is None:
                    ai_status = "error"
                    ai_error = "organizer is not configured"
                else:
                    try:
                        organization = parse_organization(
                            self.organizer.organize("\n\n".join(item for item in (raw_text, transcript) if item))
                        )
                        ai_status = "completed"
                    except (OrganizationError, OSError, RuntimeError, ValueError) as exc:
                        ai_status = "error"
                        ai_error = str(exc)[:160]
        elif effective_mode != CAPTURE_ONLY:
            ai_error = "transcript pending"

        if not self.dry_run:
            self.store.write_record(
                group,
                signature,
                ai_status=ai_status,
                ai_error=ai_error,
                processing_mode=effective_mode,
            )
            if organization is not None:
                self.store.update_organization(record_path, organization)

        state_status = "error" if ai_error and ai_status == "error" else ai_status
        self.state.set(
            group.record_id,
            {
                "signature": signature,
                "status": state_status,
                "processing_mode": effective_mode,
                "updated_at": self.state.clock(),
                "sources": [str(path) for path in group.all_sources],
                "commit_pending": False,
            },
        )
        if not self.dry_run:
            self.state.save()

        commit: str | None = None
        if not self.dry_run and self.auto_commit and self.committer is not None:
            try:
                commit = self.committer.commit(record_path, group.record_id, self.state.path)
            except (GitCommitError, OSError, RuntimeError) as exc:
                pending_state = self.state.get(group.record_id) or {}
                pending_state["commit_pending"] = True
                self.state.set(group.record_id, pending_state)
                self.state.save()
                return {
                    "record_id": group.record_id,
                    "status": "error",
                    "error": str(exc)[:160],
                    "path": str(record_path),
                }

        return {
            "record_id": group.record_id,
            "status": ai_status,
            "sources": len(group.all_sources),
            "audio": len(group.audio),
            "transcript": bool(transcript),
            "commit": commit,
            "path": str(record_path),
            **({"error": ai_error} if ai_error else {}),
        }

    def scan(self) -> list[dict[str, Any]]:
        results = [self.process(group) for group in self.scanner.scan()]
        for error in getattr(self.scanner, "errors", ()):
            results.append({"record_id": "source-scan", "status": "deferred", "error": error})
        return results

    def process_group(self, group: RecordGroup) -> dict[str, Any]:
        """Compatibility spelling for callers migrating from the prototype."""

        return self.process(group)

    def watch(self, interval: float) -> None:
        while True:
            for result in self.scan():
                if result.get("status") != "unchanged":
                    print(result, flush=True)
            time.sleep(interval)


def pipeline_from_settings(
    settings: Settings,
    *,
    metadata_reader: MetadataReader | Callable[..., Any] | None = None,
    transport: Any | None = None,
    git_runner: CommandRunner | None = None,
    clock: Callable[[], str] | None = None,
) -> RecordPipeline:
    scanners = [SourceScanner(settings.sources, metadata_reader=metadata_reader)]
    if settings.apple_notes_database is not None:
        scanners.append(
            AppleNotesScanner(
                settings.apple_notes_database,
                settings.vault / ".bridge/apple-notes-sources",
                include_deleted=settings.include_deleted_notes,
            )
        )
    scanner = CompositeScanner(scanners)
    store = RecordStore(settings.vault, clock=clock or utc_now)
    state = StateStore(settings.state_path, clock=clock or utc_now)
    organizer = OpenAICompatibleOrganizer(
        settings.endpoint,
        settings.model,
        api_key=settings.api_key,
        reasoning_effort=settings.reasoning_effort,
        timeout=settings.timeout,
        transport=transport,
    )
    committer = GitCommitter(settings.vault, runner=git_runner)
    return RecordPipeline(
        scanner,
        store,
        organizer,
        state,
        committer=committer,
        mode=settings.mode,
        auto_commit=settings.auto_commit,
        retry_ai=settings.retry_ai,
        dry_run=settings.dry_run,
    )
