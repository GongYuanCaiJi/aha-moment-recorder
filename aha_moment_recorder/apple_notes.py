"""Read existing Apple Notes into the same record pipeline as file sources.

Apple Notes keeps its content in a private SQLite database and stores many
attachments outside the note row.  This adapter deliberately keeps the
third-party parser optional: the portable core still works without it, while
macOS users can opt into existing-note import with ``apple-notes-parser``.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

from .sources import RecordGroup, ScannerError, slug


DEFAULT_DATABASE = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"


class AppleNotesImportError(ScannerError):
    """Raised when Apple Notes cannot be read or an attachment cannot be staged."""


def _write_if_changed(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            if path.read_bytes() == data:
                return
        except OSError:
            pass
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_bytes(data)
    temporary.replace(path)


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _date_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value) or None


def _folder_name(note: Any) -> str:
    folder = getattr(note, "folder", None)
    return _text(getattr(folder, "name", folder)).strip()


def _attachment_suffix(attachment: Any) -> str:
    extension = _text(getattr(attachment, "file_extension", "")).strip().lower()
    if extension:
        return extension if extension.startswith(".") else f".{extension}"
    filename = _text(getattr(attachment, "filename", "")).strip()
    suffix = Path(filename).suffix.lower()
    if suffix:
        return suffix
    uti = _text(getattr(attachment, "type_uti", "")).lower()
    known = {
        "com.apple.m4a-audio": ".m4a",
        "public.jpeg": ".jpg",
        "public.png": ".png",
        "public.heic": ".heic",
        "com.adobe.pdf": ".pdf",
        "public.mpeg-4": ".mp4",
        "public.movie": ".mov",
    }
    return known.get(uti, ".bin")


def _attachment_name(attachment: Any, index: int) -> str:
    filename = _text(getattr(attachment, "filename", "")).strip()
    stem = Path(filename).stem if filename else "attachment"
    return f"{index:03d}-{slug(stem) or 'attachment'}{_attachment_suffix(attachment)}"


class AppleNotesScanner:
    """Materialize Apple Notes into stable local source files and groups."""

    def __init__(
        self,
        database_path: Path,
        staging_root: Path,
        *,
        include_deleted: bool = False,
        notes_container_path: Path | None = None,
        parser_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.staging_root = Path(staging_root).expanduser().resolve()
        self.include_deleted = include_deleted
        self.notes_container_path = (
            Path(notes_container_path).expanduser().resolve()
            if notes_container_path is not None
            else self.database_path.parent
        )
        self.parser_factory = parser_factory

    @staticmethod
    def dependency_available() -> bool:
        try:
            import apple_notes_parser  # noqa: F401
        except ImportError:
            return False
        return True

    def _parser(self) -> Any:
        if not self.database_path.is_file():
            raise AppleNotesImportError(f"Apple Notes database not found: {self.database_path}")
        factory = self.parser_factory
        if factory is None:
            try:
                from apple_notes_parser import AppleNotesParser
            except ImportError as exc:
                raise AppleNotesImportError(
                    "Apple Notes import needs apple-notes-parser; install "
                    "the macOS extra with: python3 -m pip install 'aha-moment-recorder[macos]'"
                ) from exc
            factory = AppleNotesParser
        try:
            parser = factory(str(self.database_path))
            parser.load_data()
            return parser
        except Exception as exc:
            raise AppleNotesImportError(f"cannot read Apple Notes database: {exc}") from exc

    def _stage_attachment(self, attachment: Any, destination: Path) -> bool:
        try:
            saved = attachment.save_attachment(
                destination,
                notes_container_path=self.notes_container_path,
                prefer_media_file=True,
            )
        except Exception:
            return False
        return bool(saved and destination.is_file())

    def _group(self, note: Any) -> RecordGroup:
        stable = _text(getattr(note, "uuid", "")).strip()
        if not stable:
            stable = f"id-{getattr(note, 'note_id', getattr(note, 'id', 'unknown'))}"
        note_dir = self.staging_root / slug(stable)
        raw_path = note_dir / "raw-note.txt"
        _write_if_changed(raw_path, _text(getattr(note, "content", "")).encode("utf-8"))

        audio: list[Path] = []
        attachments: list[Path] = []
        missing: list[str] = []
        note_attachments: Iterable[Any] = getattr(note, "attachments", ()) or ()
        for index, attachment in enumerate(note_attachments, start=1):
            name = _attachment_name(attachment, index)
            destination = note_dir / name
            if not self._stage_attachment(attachment, destination):
                missing.append(_text(getattr(attachment, "filename", "")) or name)
                continue
            if getattr(attachment, "is_audio", False):
                audio.append(destination)
            else:
                attachments.append(destination)

        title = _text(getattr(note, "title", "")).strip() or "未命名備忘錄"
        captured_at = _date_value(
            getattr(note, "modification_date", None)
            or getattr(note, "creation_date", None)
        )
        return RecordGroup(
            key=f"apple-note-{stable}",
            title=title,
            source_type="apple-note",
            audio=audio,
            raw_text=[raw_path],
            attachments=attachments,
            missing_attachments=missing,
            captured_at=captured_at,
        )

    def scan(self) -> list[RecordGroup]:
        parser = self._parser()
        groups: list[RecordGroup] = []
        for note in getattr(parser, "notes", ()):
            if not self.include_deleted and _folder_name(note).casefold() == "recently deleted":
                continue
            groups.append(self._group(note))
        return sorted(groups, key=lambda item: item.record_id)
