"""Source discovery and normalization for record groups.

The scanner knows about file names and supported formats only.  Metadata such as
Voice Memos' optional UUID can be supplied through an injected reader, which
keeps the core usable on machines without macOS tools or media utilities.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol


AUDIO_SUFFIXES = frozenset({".m4a", ".mp3", ".wav", ".caf", ".aif", ".aiff", ".flac"})
TEXT_SUFFIXES = frozenset({".txt", ".md", ".markdown"})
ATTACHMENT_SUFFIXES = frozenset(
    {
        ".avi",
        ".csv",
        ".doc",
        ".docx",
        ".gif",
        ".heic",
        ".html",
        ".jpeg",
        ".jpg",
        ".json",
        ".mov",
        ".mp4",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".rtf",
        ".svg",
        ".tsv",
        ".webp",
        ".xls",
        ".xlsx",
        ".xml",
        ".zip",
    }
)
IGNORED_NAMES = frozenset({".ds_store"})
TRANSCRIPT_SUFFIXES = (
    ".transcript.txt",
    ".transcript.md",
    ".transcript.markdown",
    "-transcript.txt",
    "-transcript.md",
    "-transcript.markdown",
    "_transcript.txt",
    "_transcript.md",
    "_transcript.markdown",
)


@dataclass(frozen=True)
class SourceMetadata:
    """Optional metadata used to make a source group more stable."""

    title: str | None = None
    voice_memo_uuid: str | None = None
    captured_at: str | None = None


class MetadataReader(Protocol):
    def read(self, path: Path) -> SourceMetadata: ...


class Scanner(Protocol):
    """Small scanner contract shared by file and database-backed sources."""

    def scan(self) -> list["RecordGroup"]: ...


class ScannerError(RuntimeError):
    """A source could not be read during this scan and should be retried."""


class FileMetadataReader:
    """Portable fallback metadata reader with no external command dependency."""

    def read(self, path: Path) -> SourceMetadata:
        return SourceMetadata(title=path.stem)


class FFprobeMetadataReader:
    """Optional Voice Memos metadata adapter.

    ``ffprobe`` is deliberately an adapter, not a package dependency.  Tests
    can inject a runner or use ``FileMetadataReader`` on any platform.
    """

    def __init__(
        self,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self._runner = runner or subprocess.run

    def _tag(self, path: Path, name: str) -> str | None:
        result = self._runner(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                f"format_tags={name}",
                "-of",
                "default=nw=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        match = re.search(rf"(?:TAG:)?{re.escape(name)}=(.+)", result.stdout, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def read(self, path: Path) -> SourceMetadata:
        return SourceMetadata(
            title=self._tag(path, "title") or path.stem,
            voice_memo_uuid=self._tag(path, "voice-memo-uuid"),
            captured_at=self._tag(path, "creation_time"),
        )


@dataclass
class RecordGroup:
    """Normalized sources that belong to one record directory."""

    key: str
    title: str
    source_type: str
    audio: list[Path] = field(default_factory=list)
    raw_text: list[Path] = field(default_factory=list)
    transcript: list[Path] = field(default_factory=list)
    attachments: list[Path] = field(default_factory=list)
    missing_attachments: list[str] = field(default_factory=list)
    captured_at: str | None = field(default=None, repr=False)

    @property
    def record_id(self) -> str:
        prefix = "vm" if self.source_type == "voice-memo" else "note"
        return f"{prefix}-{slug(self.key).lower()}"

    @property
    def all_sources(self) -> list[Path]:
        return [*self.audio, *self.raw_text, *self.transcript, *self.attachments]


def slug(value: str) -> str:
    """Return a filesystem-safe, deterministic record identifier fragment."""

    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return result or "record"


def normalize_key(path: Path) -> str:
    name = path.name.lower()
    for suffix in TRANSCRIPT_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem.lower()


def is_transcript(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in TRANSCRIPT_SUFFIXES)


def _coerce_metadata(value: Any, path: Path) -> SourceMetadata:
    if isinstance(value, SourceMetadata):
        return value
    if isinstance(value, Mapping):
        return SourceMetadata(
            title=str(value["title"]) if value.get("title") else path.stem,
            voice_memo_uuid=(
                str(value["voice_memo_uuid"]) if value.get("voice_memo_uuid") else None
            ),
            captured_at=(str(value["captured_at"]) if value.get("captured_at") else None),
        )
    return SourceMetadata(title=path.stem)


class SourceScanner:
    """Discover and group supported source files below configured roots."""

    def __init__(
        self,
        roots: Iterable[Path],
        *,
        metadata_reader: MetadataReader | Callable[[Path], SourceMetadata] | None = None,
        after_epoch: float | None = None,
    ) -> None:
        self.roots = tuple(Path(root).expanduser().resolve() for root in roots)
        self.metadata_reader = metadata_reader or FileMetadataReader()
        self.after_epoch = after_epoch

    def iter_files(self) -> list[Path]:
        found: list[Path] = []
        seen: set[str] = set()
        for root in self.roots:
            if not root.exists():
                raise ScannerError(f"source root is unavailable: {root}")
            if not root.is_dir():
                raise ScannerError(f"source root is not a directory: {root}")
            try:
                paths = sorted(root.rglob("*"), key=lambda item: str(item))
            except OSError as exc:
                raise ScannerError(f"cannot read source root {root}: {exc}") from exc
            for path in paths:
                if not path.is_file() or path.name.lower() in IGNORED_NAMES:
                    continue
                if "." not in path.name or path.name.startswith("."):
                    continue
                if path.suffix.lower() not in (
                    AUDIO_SUFFIXES | TEXT_SUFFIXES | ATTACHMENT_SUFFIXES
                ):
                    continue
                identity = str(path.resolve())
                if identity in seen:
                    continue
                seen.add(identity)
                found.append(path)
        return found

    def _metadata(self, path: Path) -> SourceMetadata:
        try:
            reader = self.metadata_reader
            if callable(reader):
                value = reader(path)
            else:
                value = reader.read(path)
            return _coerce_metadata(value, path)
        except (OSError, RuntimeError, ValueError):
            return SourceMetadata(title=path.stem)

    @staticmethod
    def _register_aliases(aliases: dict[str, str], path: Path, group_key: str) -> None:
        values = {normalize_key(path), path.stem.lower()}
        for value in values:
            if value:
                aliases.setdefault(value, group_key)

    @staticmethod
    def _find_group(aliases: Mapping[str, str], path: Path) -> str | None:
        values = (normalize_key(path), path.stem.lower())
        for value in values:
            group_key = aliases.get(value)
            if group_key:
                return group_key
        return None

    def scan(self) -> list[RecordGroup]:
        files = self.iter_files()
        audios = [path for path in files if path.suffix.lower() in AUDIO_SUFFIXES]
        texts = [path for path in files if path.suffix.lower() in TEXT_SUFFIXES]
        attachments = [
            path
            for path in files
            if path.suffix.lower() in ATTACHMENT_SUFFIXES
            and path.suffix.lower() not in AUDIO_SUFFIXES
            and path.suffix.lower() not in TEXT_SUFFIXES
        ]
        groups: dict[str, RecordGroup] = {}
        aliases: dict[str, str] = {}

        for path in audios:
            metadata = self._metadata(path)
            group_key = (metadata.voice_memo_uuid or normalize_key(path)).lower()
            group = groups.setdefault(
                group_key,
                RecordGroup(
                    group_key,
                    metadata.title or path.stem,
                    "voice-memo",
                    captured_at=metadata.captured_at,
                ),
            )
            group.audio.append(path)
            self._register_aliases(aliases, path, group_key)
            if metadata.voice_memo_uuid:
                aliases.setdefault(metadata.voice_memo_uuid.lower(), group_key)

        unmatched_texts: list[Path] = []
        for path in texts:
            group_key = self._find_group(aliases, path)
            if group_key is None:
                unmatched_texts.append(path)
                continue
            group = groups[group_key]
            if is_transcript(path):
                group.transcript.append(path)
            else:
                group.raw_text.append(path)
            self._register_aliases(aliases, path, group_key)

        for path in unmatched_texts:
            group_key = normalize_key(path)
            transcript = is_transcript(path)
            group = groups.setdefault(
                group_key,
                RecordGroup(group_key, group_key, "transcript" if transcript else "text"),
            )
            if transcript:
                group.transcript.append(path)
            else:
                group.raw_text.append(path)
            self._register_aliases(aliases, path, group_key)

        for path in attachments:
            group_key = self._find_group(aliases, path)
            if group_key is None:
                group_key = normalize_key(path)
                groups.setdefault(group_key, RecordGroup(group_key, path.stem, "attachment"))
            groups[group_key].attachments.append(path)
            self._register_aliases(aliases, path, group_key)

        for group in groups.values():
            if group.source_type == "transcript" and group.raw_text:
                group.source_type = "text"

        selected: Iterable[RecordGroup] = groups.values()
        if self.after_epoch is not None:
            selected = (
                group
                for group in selected
                if any(path.stat().st_mtime >= self.after_epoch for path in group.all_sources)
            )
        return sorted(selected, key=lambda item: item.record_id)


class CompositeScanner:
    """Combine multiple source adapters into one deterministic scan."""

    def __init__(self, scanners: Iterable[Scanner]) -> None:
        self.scanners = tuple(scanners)
        self.errors: list[str] = []

    @property
    def after_epoch(self) -> float | None:
        for scanner in self.scanners:
            if hasattr(scanner, "after_epoch"):
                return getattr(scanner, "after_epoch")
        return None

    @after_epoch.setter
    def after_epoch(self, value: float | None) -> None:
        for scanner in self.scanners:
            if hasattr(scanner, "after_epoch"):
                setattr(scanner, "after_epoch", value)

    def scan(self) -> list[RecordGroup]:
        groups: list[RecordGroup] = []
        self.errors = []
        for scanner in self.scanners:
            try:
                groups.extend(scanner.scan())
            except ScannerError as exc:
                self.errors.append(str(exc))
        return sorted(groups, key=lambda item: item.record_id)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_signature(group: RecordGroup) -> str:
    """Hash source identities and bytes so sidecars trigger a new scan."""

    digest = hashlib.sha256()
    for path in sorted(group.all_sources, key=lambda item: str(item)):
        digest.update(str(path).encode("utf-8"))
        digest.update(sha256_file(path).encode("ascii"))
    return digest.hexdigest()
