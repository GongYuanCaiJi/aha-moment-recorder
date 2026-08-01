"""Record directory storage and Markdown rendering.

The store owns the invariant that source sections are rendered from source
files and that organization can only replace the marked AI section.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .organization import Organization, parse_organization
from .sources import RecordGroup, sha256_file
from .state import utc_now


def yaml_value(value: str | int | float | bool | None) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(str(value), ensure_ascii=False)


def extract_frontmatter(markdown: str) -> dict[str, str]:
    if not markdown.startswith("---\n"):
        return {}
    end = markdown.find("\n---\n", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in markdown[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip('"')
    return result


def parse_ai_section(markdown: str) -> str | None:
    match = re.search(r"(?m)^## AI 整理\s*$", markdown)
    return markdown[match.start() :].strip() if match else None


def normalize_topics(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def render_structured(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value).strip()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".part",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def safe_copy(src: Path, dest: Path) -> None:
    """Copy a source atomically without modifying the source file."""

    src = Path(src)
    dest = Path(dest)
    if src.resolve() == dest.resolve():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha256_file(src) == sha256_file(dest):
        return
    with tempfile.NamedTemporaryFile(
        dir=dest.parent,
        prefix=f".{dest.name}.",
        suffix=".part",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        with src.open("rb") as source:
            shutil.copyfileobj(source, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, dest)
    try:
        shutil.copystat(src, dest, follow_symlinks=True)
    except OSError:
        pass


class RecordStore:
    """Persist one ``records/<record-id>/`` directory at a time."""

    def __init__(self, vault: Path, *, clock: Callable[[], str] = utc_now) -> None:
        self.vault = Path(vault).expanduser().resolve()
        self.clock = clock

    def record_path(self, group: RecordGroup) -> Path:
        return self.vault / "records" / group.record_id / "record.md"

    def read(self, group: RecordGroup) -> str | None:
        path = self.record_path(group)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def raw_content(self, group: RecordGroup) -> tuple[str, str]:
        raw_text = "\n\n".join(
            path.read_text(encoding="utf-8").strip() for path in group.raw_text
        ).strip()
        transcript = "\n\n".join(
            path.read_text(encoding="utf-8").strip() for path in group.transcript
        ).strip()
        return raw_text, transcript

    @staticmethod
    def _unique_name(name: str, used: set[str]) -> str:
        if name not in used:
            used.add(name)
            return name
        path = Path(name)
        index = 2
        while True:
            candidate = f"{path.stem}-{index:02d}{path.suffix}"
            if candidate not in used:
                used.add(candidate)
                return candidate
            index += 1

    def source_destinations(self, group: RecordGroup) -> dict[Path, str]:
        destinations: dict[Path, str] = {}
        used: set[str] = set()
        for index, path in enumerate(group.audio, start=1):
            suffix = path.suffix.lower()
            name = f"raw-audio{suffix}" if index == 1 else f"raw-audio-{index:02d}{suffix}"
            destinations[path] = self._unique_name(name, used)
        for index, path in enumerate(group.raw_text, start=1):
            destinations[path] = self._unique_name(
                f"raw-text-{index:02d}{path.suffix.lower()}", used
            )
        for index, path in enumerate(group.transcript, start=1):
            destinations[path] = self._unique_name(
                f"transcript-{index:02d}{path.suffix.lower()}", used
            )
        for path in group.attachments:
            destinations[path] = self._unique_name(f"attachment-{path.name}", used)
        return destinations

    def copy_sources(self, group: RecordGroup) -> dict[Path, str]:
        record_dir = self.record_path(group).parent
        destinations = self.source_destinations(group)
        for source, name in destinations.items():
            safe_copy(source, record_dir / "attachments" / name)
        return destinations

    def _initial_ai_section(self, ai_status: str, ai_error: str | None) -> str:
        section = ["## AI 整理", "", "<!-- aha-bridge:ai -->"]
        if ai_status == "skipped":
            section.append("狀態：只收錄（未啟用 AI 整理）")
        elif ai_status == "completed":
            section.append("狀態：已完成")
        elif ai_status == "error":
            section.append(f"狀態：處理失敗（{ai_error or 'unknown'}）")
        else:
            section.append("狀態：等待逐字稿或 AI 整理")
        section.append("<!-- /aha-bridge:ai -->")
        return "\n".join(section)

    def render_raw(
        self,
        group: RecordGroup,
        signature: str,
        existing: str | None,
        *,
        ai_status: str,
        ai_error: str | None = None,
        processing_mode: str,
    ) -> str:
        raw_text, transcript = self.raw_content(group)
        existing_frontmatter = extract_frontmatter(existing or "")
        captured = existing_frontmatter.get("captured_at") or group.captured_at or self.clock()
        destinations = self.source_destinations(group)
        lines = [
            "---",
            f"record_id: {yaml_value(group.record_id)}",
            f"source_type: {yaml_value(group.source_type)}",
            f"title: {yaml_value(group.title)}",
            f"captured_at: {yaml_value(captured)}",
            f"processing_mode: {yaml_value(processing_mode)}",
            'source_status: "preserved"',
            f"ai_status: {yaml_value(ai_status)}",
            f"source_hash: {yaml_value(signature)}",
            "source_files:",
        ]
        lines.extend(f"  - {yaml_value(path.name)}" for path in group.all_sources)
        lines.extend(["---", "", f"# {group.title}", "", "## 原始資訊", ""])
        if raw_text:
            lines.extend(["### 原始文字", "", raw_text, ""])
            raw_links = [destinations[path] for path in group.raw_text]
            if raw_links:
                lines.extend(["原始檔案：" + "、".join(f"[[attachments/{name}]]" for name in raw_links), ""])
        if group.audio:
            lines.extend(["### 原始音訊", ""])
            for path in group.audio:
                lines.append(f"![[attachments/{destinations[path]}]]")
            lines.append("")
        if transcript:
            lines.extend(["### 逐字稿", "", transcript, ""])
            transcript_links = [destinations[path] for path in group.transcript]
            if transcript_links:
                lines.extend(["原始檔案：" + "、".join(f"[[attachments/{name}]]" for name in transcript_links), ""])
        elif group.audio:
            lines.extend(
                [
                    "### 逐字稿",
                    "",
                    "尚未取得逐字稿。音訊檔案已保留；把同名 `.transcript.txt` 放進收件匣後會自動補上。",
                    "",
                ]
            )
        if group.attachments:
            lines.extend(["### 附件", ""])
            for path in group.attachments:
                lines.append(f"- [[attachments/{destinations[path]}]]（{path.name}）")
            lines.append("")

        preserved_ai = parse_ai_section(existing or "")
        if preserved_ai and ai_status not in {"pending", "error"}:
            ai_section = preserved_ai
        else:
            ai_section = self._initial_ai_section(ai_status, ai_error)
        lines.extend([ai_section.strip(), ""])
        return "\n".join(lines)

    def write_record(
        self,
        group: RecordGroup,
        signature: str,
        *,
        ai_status: str,
        ai_error: str | None = None,
        processing_mode: str,
    ) -> Path:
        path = self.record_path(group)
        existing = self.read(group)
        content = self.render_raw(
            group,
            signature,
            existing,
            ai_status=ai_status,
            ai_error=ai_error,
            processing_mode=processing_mode,
        )
        if existing != content:
            _atomic_write(path, content)
        return path

    def update_organization(self, record_path: Path, result: Organization | Any) -> None:
        organization = parse_organization(result)
        existing = Path(record_path).read_text(encoding="utf-8")
        marker = re.search(r"(?m)^## AI 整理\s*$", existing)
        prefix = existing[: marker.start()].rstrip() if marker else existing.rstrip()
        topics = normalize_topics(organization.topic)
        section = "\n".join(
            [
                "## AI 整理",
                "",
                "<!-- aha-bridge:ai -->",
                "狀態：已完成",
                "<!-- /aha-bridge:ai -->",
                "",
                "### 分類",
                "",
                organization.classification,
                "",
                "### 主題",
                "",
                "、".join(topics) if topics else "（無）",
                "",
                "### 結構化輸出",
                "",
                render_structured(organization.structured_output),
                "",
                "### 摘要",
                "",
                organization.summary,
            ]
        )
        _atomic_write(Path(record_path), prefix + "\n\n" + section + "\n")
