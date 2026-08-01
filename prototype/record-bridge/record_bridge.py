#!/usr/bin/env python3
"""Background bridge from Apple capture files to one Obsidian record.

The bridge deliberately treats the Vault as the long-term record book:

* source audio, source text, transcript, and attachments live below one
  ``records/<record-id>/`` directory;
* AI output is appended to the same ``record.md`` and never replaces source
  sections;
* a small state file makes scans idempotent and lets a later transcript sidecar
  trigger the same record again;
* when the Vault is a Git worktree, each changed record is committed.

It uses only the Python standard library.  A source directory may be either
the macOS Voice Memos synced Recordings directory or an iCloud/Files inbox
written by an iPhone Shortcut.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIO_SUFFIXES = {".m4a", ".mp3", ".wav", ".caf", ".aif", ".aiff", ".flac"}
TEXT_SUFFIXES = {".txt", ".md", ".markdown"}
IGNORED_NAMES = {".ds_store"}
DEFAULT_VOICE_MEMOS = (
    Path.home()
    / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
DEFAULT_INBOX = (
    Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/AhaMomentInbox"
)
DEFAULT_VAULT = Path.home() / "Documents/Aha Moment Vault"
DEFAULT_PROXY_URL = "http://127.0.0.1:8317/v1"
DEFAULT_MODEL = "gpt-5.6-luna"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-._") or "record"


def normalize_key(path: Path) -> str:
    name = path.name.lower()
    for suffix in (".transcript.txt", ".transcript.md", "-transcript.txt", "-transcript.md", "_transcript.txt", "_transcript.md"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem.lower()


def short_token(value: str) -> str:
    token = value.rsplit("-", 1)[-1]
    return token.lower()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def safe_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha256_file(src) == sha256_file(dest):
        return
    with tempfile.NamedTemporaryFile(
        dir=dest.parent, prefix=f".{dest.name}.", suffix=".part", delete=False
    ) as handle:
        temporary = Path(handle.name)
        with src.open("rb") as source:
            shutil.copyfileobj(source, handle)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, dest)
    shutil.copystat(src, dest, follow_symlinks=True)


def command_output(args: list[str], timeout: float = 10.0) -> str:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def voice_memo_uuid(path: Path) -> str | None:
    """Read the public container tag written by Voice Memos, if present."""

    output = command_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=voice-memo-uuid",
            "-of",
            "default=nw=1",
            str(path),
        ],
        timeout=8,
    )
    match = re.search(r"(?:TAG:)?voice-memo-uuid=(.+)", output, re.IGNORECASE)
    return match.group(1).strip() if match else None


def audio_title(path: Path) -> str:
    output = command_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=title",
            "-of",
            "default=nw=1",
            str(path),
        ],
        timeout=8,
    )
    match = re.search(r"(?:TAG:)?title=(.+)", output, re.IGNORECASE)
    return match.group(1).strip() if match else path.stem


def captured_at(path: Path) -> str:
    output = command_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=creation_time",
            "-of",
            "default=nw=1",
            str(path),
        ],
        timeout=8,
    )
    match = re.search(r"(?:TAG:)?creation_time=(.+)", output, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SourceGroup:
    key: str
    title: str
    source_type: str
    audio: list[Path] = field(default_factory=list)
    raw_text: list[Path] = field(default_factory=list)
    transcript: list[Path] = field(default_factory=list)
    attachments: list[Path] = field(default_factory=list)

    @property
    def record_id(self) -> str:
        prefix = "vm" if self.source_type == "voice-memo" else "note"
        return f"{prefix}-{slug(self.key).lower()}"

    @property
    def all_sources(self) -> list[Path]:
        return [*self.audio, *self.raw_text, *self.transcript, *self.attachments]


def iter_files(roots: Iterable[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.name.lower() in IGNORED_NAMES:
                continue
            if "." not in path.name or path.name.startswith("."):
                continue
            if path.suffix.lower() in AUDIO_SUFFIXES or path.suffix.lower() in TEXT_SUFFIXES:
                found.append(path)
    return sorted(found, key=lambda item: str(item))


def source_groups(roots: list[Path], after_epoch: float | None = None) -> list[SourceGroup]:
    files = iter_files(roots)
    audios = [path for path in files if path.suffix.lower() in AUDIO_SUFFIXES]
    texts = [path for path in files if path.suffix.lower() in TEXT_SUFFIXES]
    groups: dict[str, SourceGroup] = {}
    audio_keys: dict[str, str] = {}

    for path in audios:
        uuid = voice_memo_uuid(path)
        key = uuid or path.stem
        group_key = key.lower()
        group = groups.setdefault(
            group_key,
            SourceGroup(group_key, audio_title(path), "voice-memo"),
        )
        group.audio.append(path)
        audio_keys[normalize_key(path)] = group_key
        audio_keys[short_token(normalize_key(path))] = group_key
        if uuid:
            audio_keys[uuid.lower()] = group_key

    unmatched_texts: list[Path] = []
    for path in texts:
        key = normalize_key(path)
        group_key = audio_keys.get(key) or audio_keys.get(short_token(key))
        if group_key is None:
            unmatched_texts.append(path)
            continue
        group = groups[group_key]
        name = path.name.lower()
        is_transcript = (
            ".transcript." in name
            or name.endswith("-transcript.txt")
            or name.endswith("-transcript.md")
            or name.endswith("_transcript.txt")
            or name.endswith("_transcript.md")
        )
        if is_transcript:
            group.transcript.append(path)
        else:
            group.raw_text.append(path)

    for path in unmatched_texts:
        key = normalize_key(path)
        if key.endswith(".transcript"):
            key = key.removesuffix(".transcript")
        group_key = key
        groups.setdefault(group_key, SourceGroup(group_key, path.stem, "text")).raw_text.append(path)

    selected = groups.values()
    if after_epoch is not None:
        selected = (
            group
            for group in selected
            if any(path.stat().st_mtime >= after_epoch for path in group.all_sources)
        )
    return sorted(selected, key=lambda item: item.record_id)


def yaml_value(value: str | int | float | bool | None) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(str(value), ensure_ascii=False)


def parse_ai_section(markdown: str) -> str | None:
    match = re.search(r"(?m)^## AI 整理\s*$", markdown)
    return markdown[match.start() :].strip() if match else None


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


def normalize_topics(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def render_structured(value: Any) -> str:
    """Keep nested model output readable instead of Python repr syntax."""

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value).strip()


def parse_json_response(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group(0)
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("AI response is not an object")
    required = {"classification", "topic", "structured_output", "summary"}
    missing = sorted(required - value.keys())
    if missing:
        raise ValueError(f"AI response missing: {', '.join(missing)}")
    return value


class Bridge:
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
        self.vault = vault.expanduser().resolve()
        self.sources = [path.expanduser().resolve() for path in sources]
        self.state_path = (state_path or self.vault / ".bridge/state.json").expanduser().resolve()
        self.proxy_url = proxy_url.rstrip("/")
        self.model = model
        self.mode = mode
        self.auto_commit = auto_commit
        self.retry_ai = retry_ai
        self.dry_run = dry_run
        self.after_epoch = after_epoch
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {"version": 1, "groups": {}}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"version": 1, "groups": {}}
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "groups": {}}

    def _save_state(self) -> None:
        if self.dry_run:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        temporary = self.state_path.with_suffix(".json.part")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, self.state_path)

    def _group_signature(self, group: SourceGroup) -> str:
        digest = hashlib.sha256()
        for path in sorted(group.all_sources, key=lambda item: str(item)):
            digest.update(str(path).encode())
            digest.update(sha256_file(path).encode())
        return digest.hexdigest()

    def _record_path(self, group: SourceGroup) -> Path:
        return self.vault / "records" / group.record_id / "record.md"

    def _raw_content(self, group: SourceGroup) -> tuple[str, str]:
        raw_text = "\n\n".join(read_text(path).strip() for path in group.raw_text).strip()
        transcript = "\n\n".join(read_text(path).strip() for path in group.transcript).strip()
        return raw_text, transcript

    def _render_record(
        self,
        group: SourceGroup,
        signature: str,
        existing: str | None,
        ai_status: str,
        ai_error: str | None = None,
    ) -> str:
        raw_text, transcript = self._raw_content(group)
        existing_frontmatter = extract_frontmatter(existing or "")
        captured = existing_frontmatter.get("captured_at")
        if not captured:
            first = group.audio[0] if group.audio else group.all_sources[0]
            captured = captured_at(first)
        source_names = [path.name for path in group.all_sources]
        lines = [
            "---",
            f"record_id: {yaml_value(group.record_id)}",
            f"source_type: {yaml_value(group.source_type)}",
            f"title: {yaml_value(group.title)}",
            f"captured_at: {yaml_value(captured)}",
            f"processing_mode: {yaml_value(self.mode)}",
            "source_status: \"preserved\"",
            f"ai_status: {yaml_value(ai_status)}",
            f"source_hash: {yaml_value(signature)}",
            "source_files:",
        ]
        lines.extend(f"  - {yaml_value(name)}" for name in source_names)
        lines.extend(["---", "", f"# {group.title}", "", "## 原始資訊", ""])
        if raw_text:
            lines.extend(["### 原始文字", "", raw_text, ""])
        if group.audio:
            lines.extend(["### 原始音訊", ""])
            for index, path in enumerate(group.audio, start=1):
                filename = "raw-audio.m4a" if index == 1 else f"raw-audio-{index:02d}{path.suffix.lower()}"
                lines.append(f"![[attachments/{filename}]]")
            lines.append("")
        if transcript:
            lines.extend(["### 逐字稿", "", transcript, ""])
        else:
            lines.extend(
                [
                    "### 逐字稿",
                    "",
                    "尚未取得逐字稿。音訊檔案已保留；把同名 `.transcript.txt` 放進收件匣後會自動補上。",
                    "",
                ]
            )
        extra = [path for path in group.attachments if path not in group.transcript and path not in group.raw_text]
        if extra:
            lines.extend(["### 附件", ""])
            for path in extra:
                lines.append(f"- [[attachments/{path.name}]]")
            lines.append("")

        preserved_ai = parse_ai_section(existing or "")
        if preserved_ai and ai_status not in {"pending", "error"}:
            ai_section = preserved_ai
        else:
            ai_section = "## AI 整理\n\n<!-- aha-bridge:ai -->\n"
            if ai_status == "skipped":
                ai_section += "狀態：只收錄（未啟用 AI 整理）\n"
            elif ai_status == "completed":
                ai_section += "狀態：已完成\n"
            elif ai_status == "error":
                ai_section += f"狀態：處理失敗（{ai_error or 'unknown'}）\n"
            else:
                ai_section += "狀態：等待逐字稿或 AI 整理\n"
            ai_section += "<!-- /aha-bridge:ai -->"
        lines.extend([ai_section.strip(), ""])
        return "\n".join(lines)

    def _copy_sources(self, group: SourceGroup) -> None:
        record_dir = self._record_path(group).parent
        if self.dry_run:
            return
        for index, path in enumerate(group.audio, start=1):
            name = "raw-audio.m4a" if index == 1 else f"raw-audio-{index:02d}{path.suffix.lower()}"
            safe_copy(path, record_dir / "attachments" / name)
        for path in group.attachments:
            if path in group.audio or path in group.raw_text or path in group.transcript:
                continue
            safe_copy(path, record_dir / "attachments" / path.name)

    def _proxy_key(self) -> str:
        config_path = Path.home() / "cli-proxy-api/config.yaml"
        raw = config_path.read_text(encoding="utf-8")
        tail = raw[raw.find("api-keys:") :] if "api-keys:" in raw else raw
        match = re.search(r"(?m)^\s*-\s*([^\s#]+)\s*$", tail)
        if not match:
            raise RuntimeError("cli-proxy-api/config.yaml has no api key")
        return match.group(1).strip().strip('"\'')

    def _call_luna(self, text: str) -> dict[str, Any]:
        prompt = (
            "請把下面一筆個人記錄做通用整理，只輸出 JSON，不要 Markdown code fence。"
            "欄位必須是 classification、topic、structured_output、summary。"
            "classification 是單一主要分類；topic 可是字串或字串陣列；"
            "structured_output 是忠於原意的可讀整理；summary 是簡短摘要。"
            "不要額外產生待辦欄位；若內容本身是待辦，可把待辦當作 classification。"
            "不要捏造來源沒有的資訊。\n\n記錄內容：\n" + text
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是個人記錄整理助手。"},
                {"role": "user", "content": prompt},
            ],
            "reasoning_effort": "medium",
            "temperature": 0,
        }
        request = urllib.request.Request(
            f"{self.proxy_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._proxy_key()}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"proxy HTTP {exc.code}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"proxy request failed: {type(exc).__name__}") from exc
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("proxy response has no chat content") from exc
        return parse_json_response(content)

    def _write_ai_section(self, record_path: Path, result: dict[str, Any]) -> None:
        existing = read_text(record_path)
        marker = re.search(r"(?m)^## AI 整理\s*$", existing)
        if marker:
            prefix = existing[: marker.start()].rstrip()
        else:
            prefix = existing.rstrip()
        classification = str(result.get("classification", "未分類")).strip() or "未分類"
        topics = normalize_topics(result.get("topic"))
        structured = render_structured(result.get("structured_output", ""))
        summary = str(result.get("summary", "")).strip()
        topic_text = "、".join(topics) if topics else "（無）"
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
                classification,
                "",
                "### 主題",
                "",
                topic_text,
                "",
                "### 結構化輸出",
                "",
                structured,
                "",
                "### 摘要",
                "",
                summary,
            ]
        )
        record_path.write_text(prefix + "\n\n" + section + "\n", encoding="utf-8")

    def _commit(self, record_path: Path, record_id: str) -> str | None:
        if not self.auto_commit or self.dry_run:
            return None
        try:
            root = Path(
                command_output(["git", "-C", str(self.vault), "rev-parse", "--show-toplevel"])
            )
        except (ValueError, OSError):
            return None
        if not root or root != self.vault:
            return None
        relative = record_path.parent.relative_to(self.vault)
        subprocess.run(["git", "-C", str(self.vault), "add", str(relative)], check=True)
        if self.state_path.is_file() and self.state_path.is_relative_to(self.vault):
            subprocess.run(
                ["git", "-C", str(self.vault), "add", str(self.state_path.relative_to(self.vault))],
                check=True,
            )
        status = command_output(["git", "-C", str(self.vault), "status", "--porcelain"])
        if not status:
            return None
        result = subprocess.run(
            ["git", "-C", str(self.vault), "commit", "-m", f"record: update {record_id}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("git commit failed")
        return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "committed"

    def process_group(self, group: SourceGroup) -> dict[str, Any]:
        signature = self._group_signature(group)
        previous = self.state.setdefault("groups", {}).get(group.record_id, {})
        previous_snapshot = dict(previous)
        if previous.get("signature") == signature and not self.retry_ai:
            return {"record_id": group.record_id, "status": "unchanged"}
        record_path = self._record_path(group)
        existing = read_text(record_path) if record_path.is_file() else None
        self._copy_sources(group)
        raw_text, transcript = self._raw_content(group)
        ai_status = "skipped" if self.mode == "capture-only" else "pending"
        ai_error: str | None = None
        ai_result: dict[str, Any] | None = None
        if self.mode != "capture-only" and (raw_text or transcript):
            try:
                if not self.dry_run:
                    ai_result = self._call_luna("\n\n".join(item for item in (raw_text, transcript) if item))
                if self.dry_run:
                    ai_status = "pending"
                else:
                    ai_status = "completed"
            except (RuntimeError, OSError, ValueError) as exc:
                ai_status = "error"
                ai_error = str(exc)[:120]
        elif self.mode != "capture-only":
            ai_error = "transcript pending"
        if not self.dry_run:
            content = self._render_record(group, signature, existing, ai_status, ai_error)
            if not record_path.is_file() or read_text(record_path) != content:
                record_path.parent.mkdir(parents=True, exist_ok=True)
                record_path.write_text(content, encoding="utf-8")
            # Apply the AI result after the deterministic raw rendering so a
            # source change can never erase it.
            if ai_status == "completed" and ai_result is not None:
                self._write_ai_section(record_path, ai_result)
        else:
            commit = None
        self.state["groups"][group.record_id] = {
            "signature": signature,
            "status": ai_status,
            "updated_at": utc_now(),
            "sources": [str(path) for path in group.all_sources],
        }
        if not self.dry_run:
            self._save_state()
            try:
                commit = self._commit(record_path, group.record_id)
            except Exception:
                if previous_snapshot:
                    self.state["groups"][group.record_id] = previous_snapshot
                else:
                    self.state["groups"].pop(group.record_id, None)
                self._save_state()
                raise
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
        results = [self.process_group(group) for group in source_groups(self.sources, self.after_epoch)]
        self._save_state()
        return results

    def watch(self, interval: float) -> None:
        while True:
            for result in self.scan():
                if result.get("status") not in {"unchanged"}:
                    print(json.dumps(result, ensure_ascii=False), flush=True)
            time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--source", type=Path, action="append", dest="sources")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--proxy-url", default=DEFAULT_PROXY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--mode", choices=["capture-only", "collect-and-organize"], default="collect-and-organize")
    parser.add_argument("--no-git-commit", action="store_true")
    parser.add_argument("--retry-ai", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument(
        "--after",
        help="only process groups with at least one source file modified at/after this ISO-8601 time",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    sources = args.sources or [DEFAULT_VOICE_MEMOS, DEFAULT_INBOX]
    after_epoch = None
    if args.after:
        try:
            after_epoch = datetime.fromisoformat(args.after).timestamp()
        except ValueError as exc:
            raise SystemExit(f"invalid --after timestamp: {exc}") from exc
    bridge = Bridge(
        vault=args.vault,
        sources=sources,
        state_path=args.state,
        proxy_url=args.proxy_url,
        model=args.model,
        mode=args.mode,
        auto_commit=not args.no_git_commit,
        retry_ai=args.retry_ai,
        dry_run=args.dry_run,
        after_epoch=after_epoch,
    )
    if args.watch:
        bridge.watch(args.interval)
        return 0
    results = bridge.scan()
    print(json.dumps({"vault": str(bridge.vault), "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(item.get("status") != "error" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
