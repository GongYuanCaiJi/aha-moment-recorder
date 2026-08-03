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
from .transcription import Transcriber, TranscriptionError, WhisperCppTranscriber


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
        transcriber: Transcriber | None = None,
        auto_transcribe: bool = True,
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
        self.transcriber = transcriber
        self.auto_transcribe = auto_transcribe

    def _has_source_transcript(self, group: RecordGroup) -> bool:
        record_root = self.store.record_path(group).parent.resolve()
        return any(
            record_root not in path.expanduser().resolve().parents
            for path in group.transcript
        )

    def _missing_transcription_indexes(self, group: RecordGroup) -> list[int]:
        return [
            index
            for index in range(1, len(group.audio) + 1)
            if not self.store.generated_transcript_path(group, index).is_file()
        ]

    def _transcribe_missing(self, group: RecordGroup) -> None:
        if self.transcriber is None or not self.auto_transcribe or not group.audio:
            return
        if self._has_source_transcript(group):
            return
        for index, audio_path in enumerate(group.audio, start=1):
            destination = self.store.generated_transcript_path(group, index)
            if destination.is_file():
                if destination not in group.transcript:
                    group.transcript.append(destination)
                continue
            text = self.transcriber.transcribe(audio_path, destination)
            if not text.strip():
                raise TranscriptionError("transcription returned empty text")
            if not destination.is_file():
                raise TranscriptionError(
                    f"transcriber did not write the transcript: {destination}"
                )
            group.transcript.append(destination)

    def process(self, group: RecordGroup) -> dict[str, Any]:
        self.store.attach_generated_transcripts(group)
        needs_transcription = bool(
            self.transcriber is not None
            and self.auto_transcribe
            and group.audio
            and not self._has_source_transcript(group)
            and bool(self._missing_transcription_indexes(group))
        )
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
            and not needs_transcription
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
            and not needs_transcription
        ):
            return {"record_id": group.record_id, "status": "unchanged"}

        transcription_error: str | None = None
        try:
            if not self.dry_run:
                self.store.copy_sources(group)
                if needs_transcription:
                    self._transcribe_missing(group)
                    signature = source_signature(group)
                    # The generated transcript is already in the destination,
                    # but this keeps the copy operation idempotent for custom
                    # transcribers that write elsewhere.
                    self.store.copy_sources(group)
            raw_text, transcript = self.store.raw_content(group)
        except TranscriptionError as exc:
            transcription_error = str(exc)
            signature = source_signature(group)
            try:
                raw_text, transcript = self.store.raw_content(group)
            except OSError as source_exc:
                return {
                    "record_id": group.record_id,
                    "status": "deferred",
                    "error": f"source changed while reading: {str(source_exc)[:120]}",
                }
        except OSError as exc:
            return {
                "record_id": group.record_id,
                "status": "deferred",
                "error": f"source changed while reading: {str(exc)[:120]}",
            }
        ai_status = "skipped" if effective_mode == CAPTURE_ONLY else "pending"
        ai_error: str | None = None
        organization: Organization | None = None

        if transcription_error:
            ai_error = f"transcription failed: {transcription_error}"
            if effective_mode != CAPTURE_ONLY:
                ai_status = "error"
        elif effective_mode != CAPTURE_ONLY and (raw_text or transcript):
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

        state_status = "error" if transcription_error or (ai_error and ai_status == "error") else ai_status
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

        result_status = "error" if transcription_error else ai_status
        return {
            "record_id": group.record_id,
            "status": result_status,
            "sources": len(group.all_sources),
            "audio": len(group.audio),
            "transcript": bool(transcript),
            "transcription": "error" if transcription_error else ("completed" if transcript else "pending"),
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
    transcriber = (
        WhisperCppTranscriber(
            settings.stt_model,
            command=settings.stt_command,
            ffmpeg_command=settings.stt_ffmpeg_command,
            language=settings.stt_language,
            timeout=settings.stt_timeout,
        )
        if settings.auto_transcribe and settings.stt_model is not None
        else None
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
        transcriber=transcriber,
        auto_transcribe=settings.auto_transcribe,
    )
