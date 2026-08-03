#!/usr/bin/env python3
"""THROWAWAY PROTOTYPE — Mac capability probe and record contract scenario.

Question:
    Which parts of the Apple-capture -> Obsidian workflow can be checked on a
    Mac without touching a real vault, and does a minimal record state keep
    raw inputs intact when AI output is appended?

This is deliberately not a production test suite. It is a small, read-only
capability probe plus an in-memory scenario runner.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


APP_CANDIDATES = {
    "Obsidian": [Path("/Applications/Obsidian.app")],
    "Notes": [Path("/System/Applications/Notes.app"), Path("/Applications/Notes.app")],
    "Voice Memos": [
        Path("/System/Applications/VoiceMemos.app"),
        Path("/Applications/Voice Memos.app"),
    ],
    "Shortcuts": [
        Path("/System/Applications/Shortcuts.app"),
        Path("/Applications/Shortcuts.app"),
    ],
}


@dataclass
class Check:
    name: str
    status: str
    evidence: str


@dataclass
class RecordState:
    raw_text: str | None = None
    raw_audio: str | None = None
    transcript: str | None = None
    attachments: dict[str, str] = field(default_factory=dict)
    ai_results: list[str] = field(default_factory=list)
    synced_to_mac: bool = False


def command_output(args: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def app_info(path: Path) -> dict[str, Any] | None:
    plist_path = path / "Contents" / "Info.plist"
    if not plist_path.is_file():
        return None
    try:
        with plist_path.open("rb") as handle:
            info = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException):
        return None

    schemes: list[str] = []
    for url_type in info.get("CFBundleURLTypes", []):
        schemes.extend(url_type.get("CFBundleURLSchemes", []))
    return {
        "path": str(path),
        "bundle_id": info.get("CFBundleIdentifier"),
        "version": info.get("CFBundleShortVersionString")
        or info.get("CFBundleVersion"),
        "url_schemes": sorted(set(schemes)),
    }


def discover_apps() -> dict[str, dict[str, Any] | None]:
    discovered: dict[str, dict[str, Any] | None] = {}
    for name, candidates in APP_CANDIDATES.items():
        discovered[name] = next(
            (info for candidate in candidates if (info := app_info(candidate))),
            None,
        )
    return discovered


def mac_version() -> tuple[str, int]:
    returncode, version, _ = command_output(["/usr/bin/sw_vers", "-productVersion"])
    if returncode != 0 or not version:
        version = platform.mac_ver()[0] or "unknown"
    try:
        major = int(version.split(".", 1)[0])
    except ValueError:
        major = 0
    return version, major


def inspect_mac() -> list[Check]:
    version, major = mac_version()
    architecture = platform.machine()
    apps = discover_apps()
    checks: list[Check] = []

    checks.append(
        Check(
            "macOS",
            "PASS" if sys.platform == "darwin" else "FAIL",
            f"{version} ({architecture})",
        )
    )

    for name in ("Obsidian", "Notes", "Voice Memos", "Shortcuts"):
        info = apps[name]
        if info is None:
            checks.append(Check(f"app:{name}", "FAIL", "application bundle not found"))
        else:
            checks.append(
                Check(
                    f"app:{name}",
                    "PASS",
                    f"{info['path']} · {info['bundle_id']} · {info['version']}",
                )
            )

    shortcuts_path = shutil.which("shortcuts")
    if shortcuts_path is None:
        checks.append(Check("shortcuts-cli", "FAIL", "shortcuts executable not found"))
    else:
        returncode, stdout, stderr = command_output([shortcuts_path, "help"])
        checks.append(
            Check(
                "shortcuts-cli",
                "PASS" if returncode == 0 and "run" in stdout else "FAIL",
                f"{shortcuts_path}; help={'ok' if returncode == 0 else stderr}",
            )
        )

    osascript_path = shutil.which("osascript")
    checks.append(
        Check(
            "osascript",
            "PASS" if osascript_path else "FAIL",
            osascript_path or "osascript executable not found",
        )
    )

    obsidian = apps["Obsidian"]
    if obsidian is None:
        checks.append(Check("obsidian-uri-registration", "FAIL", "Obsidian is not installed"))
    else:
        schemes = obsidian["url_schemes"]
        checks.append(
            Check(
                "obsidian-uri-registration",
                "PASS" if "obsidian" in schemes else "FAIL",
                f"registered schemes: {', '.join(schemes) or '(none)'}",
            )
        )

    eligible = architecture in {"arm64", "aarch64"} and major >= 15
    checks.append(
        Check(
            "notes-audio-transcription-prerequisite",
            "PASS" if eligible else "MANUAL",
            "Apple silicon + macOS 15+ prerequisite is present"
            if eligible
            else "requires Apple silicon and macOS 15+; language/region still needs UI check",
        )
    )
    checks.append(
        Check(
            "voice-memos-transcription-prerequisite",
            "PASS" if eligible else "MANUAL",
            "Apple silicon + macOS 15+ prerequisite is present"
            if eligible
            else "requires Apple silicon and macOS 15+; language/region still needs UI check",
        )
    )

    checks.append(
        Check(
            "obsidian-sync-account-and-cross-device",
            "MANUAL",
            "requires a configured remote vault and a second device; probe does not touch either",
        )
    )
    return checks


def record_json(record: RecordState) -> dict[str, Any]:
    return asdict(record)


def render(action: str, record: RecordState) -> None:
    print(f"\n=== {action} ===")
    print(json.dumps(record_json(record), ensure_ascii=False, indent=2, sort_keys=True))


def assert_raw_inputs_unchanged(record: RecordState, originals: dict[str, Any]) -> None:
    for field_name in ("raw_text", "raw_audio", "transcript", "attachments"):
        actual = getattr(record, field_name)
        expected = originals[field_name]
        if actual != expected:
            raise AssertionError(f"raw input changed: {field_name}: {actual!r} != {expected!r}")


def apply_action(record: RecordState, action: str, value: Any = None) -> None:
    if action == "capture_text":
        record.raw_text = value
    elif action == "capture_audio":
        record.raw_audio = value
    elif action == "capture_transcript":
        record.transcript = value
    elif action == "attach":
        name, reference = value
        record.attachments[name] = reference
    elif action == "append_ai":
        record.ai_results.append(value)
    elif action == "sync_to_mac":
        record.synced_to_mac = True
    else:
        raise ValueError(f"unknown action: {action}")


def run_record_scenario(interactive: bool = False) -> bool:
    record = RecordState()
    originals: dict[str, Any] = {
        "raw_text": None,
        "raw_audio": None,
        "transcript": None,
        "attachments": {},
    }

    steps = [
        ("capture_text", "原始文字：Mac capture fixture / 不可覆寫"),
        ("capture_audio", "fixture-audio.m4a (synthetic reference; no file written)"),
        ("capture_transcript", "逐字稿：原始語音的可讀文字 fixture"),
        ("attach", ("fixture.pdf", "vault://fixture.pdf")),
        ("append_ai", "AI 結果 #1：獨立追加，未修改來源"),
        ("append_ai", "AI 結果 #2：重跑仍保留 #1"),
        ("sync_to_mac", None),
    ]

    for action, value in steps:
        if action == "capture_text":
            originals["raw_text"] = value
        elif action == "capture_audio":
            originals["raw_audio"] = value
        elif action == "capture_transcript":
            originals["transcript"] = value
        elif action == "attach":
            name, reference = value
            originals["attachments"][name] = reference

        apply_action(record, action, value)
        render(action, record)
        assert_raw_inputs_unchanged(record, originals)

    passed = (
        record.raw_text == originals["raw_text"]
        and record.raw_audio == originals["raw_audio"]
        and record.transcript == originals["transcript"]
        and record.attachments == originals["attachments"]
        and record.ai_results == [
            "AI 結果 #1：獨立追加，未修改來源",
            "AI 結果 #2：重跑仍保留 #1",
        ]
        and record.synced_to_mac
    )
    print(f"\nRECORD CONTRACT: {'PASS' if passed else 'FAIL'}")
    return passed


def create_synthetic_m4a(output_path: Path) -> str:
    """Create a short real AAC-in-MP4 fixture without touching user data."""
    wav_path = output_path.with_suffix(".wav")
    sample_rate = 8_000
    frame_count = sample_rate // 10
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = b"".join(
            struct.pack("<h", int(8_000 * math.sin(2 * math.pi * 440 * index / sample_rate)))
            for index in range(frame_count)
        )
        wav_file.writeframes(frames)

    converter = shutil.which("afconvert") or shutil.which("ffmpeg")
    if converter is None:
        raise RuntimeError("afconvert or ffmpeg is required to create the audio fixture")

    if Path(converter).name == "afconvert":
        result = command_output(
            [converter, "-f", "m4af", "-d", "aac", str(wav_path), str(output_path)],
            timeout=15,
        )
    else:
        result = command_output(
            [converter, "-y", "-loglevel", "error", "-i", str(wav_path), str(output_path)],
            timeout=15,
        )
    wav_path.unlink(missing_ok=True)
    if result[0] != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(result[2] or result[1] or "audio conversion failed")

    inspector = shutil.which("afinfo")
    if inspector:
        info = command_output([inspector, str(output_path)], timeout=10)
        if info[0] == 0:
            return next(
                (line.strip() for line in info[1].splitlines() if "File type ID" in line),
                "m4a fixture",
            )
    return f"m4a fixture ({output_path.stat().st_size} bytes)"


def write_record_note(
    note_path: Path,
    raw_text: str,
    audio_path: Path,
    transcript: str,
    attachment_path: Path,
    ai_results: list[str],
) -> None:
    vault_root = note_path.parent
    audio_ref = audio_path.relative_to(vault_root).as_posix()
    attachment_ref = attachment_path.relative_to(vault_root).as_posix()
    ai_sections = "\n".join(
        f"### 第 {index} 次整理\n{result}" for index, result in enumerate(ai_results, start=1)
    )
    note_path.write_text(
        f"""# Mac capture fixture

## 原始資訊

### 原始文字

{raw_text}

### 原始音訊

![[{audio_ref}]]

### 逐字稿

{transcript}

### 附件

- [[{attachment_ref}]]

## AI 整理結果

{ai_sections}
""",
        encoding="utf-8",
    )


def append_ai_result(note_path: Path, result: str) -> None:
    with note_path.open("a", encoding="utf-8") as note_file:
        existing = note_path.read_text(encoding="utf-8")
        ordinal = existing.count("### 第 ") + 1
        note_file.write(f"\n### 第 {ordinal} 次整理\n\n{result}\n")


def run_file_backed_scenario() -> tuple[bool, str]:
    """Verify one same-record Markdown note plus real attachment files."""
    raw_text = "原始文字：file-backed fixture / 不可覆寫"
    transcript = "逐字稿：由原始音訊產生的可讀文字 fixture"
    ai_results = ["分類：靈感\n主題：Mac capture\n摘要：確認原始資料與整理結果可共存"]

    try:
        with tempfile.TemporaryDirectory(prefix="aha-moment-recorder-prototype-") as scratch:
            vault = Path(scratch) / "scratch-vault"
            record_dir = vault / "records" / "mac-capture-fixture"
            attachments_dir = record_dir / "attachments"
            attachments_dir.mkdir(parents=True)
            note_path = record_dir / "record.md"
            audio_path = attachments_dir / "raw-audio.m4a"
            attachment_path = attachments_dir / "fixture.txt"
            audio_evidence = create_synthetic_m4a(audio_path)
            attachment_path.write_text("附加檔案 fixture\n", encoding="utf-8")

            write_record_note(
                note_path,
                raw_text,
                audio_path,
                transcript,
                attachment_path,
                ai_results,
            )
            raw_snapshot = note_path.read_text(encoding="utf-8")
            append_ai_result(note_path, "重跑整理：仍保留原始文字、音訊、逐字稿與附件")
            final_note = note_path.read_text(encoding="utf-8")

            required_fragments = (
                raw_text,
                transcript,
                "attachments/raw-audio.m4a",
                "attachments/fixture.txt",
                ai_results[0],
                "重跑整理：仍保留原始文字、音訊、逐字稿與附件",
            )
            if not all(fragment in final_note for fragment in required_fragments):
                raise AssertionError("same-record Markdown note lost a required fragment")
            if not audio_path.is_file() or audio_path.stat().st_size == 0:
                raise AssertionError("audio attachment was not persisted")
            if not attachment_path.is_file():
                raise AssertionError("generic attachment was not persisted")
            if raw_text not in final_note or transcript not in final_note:
                raise AssertionError("raw content was overwritten")
            if raw_snapshot == final_note:
                raise AssertionError("AI append did not create a new version of the note")

            evidence = (
                f"{note_path.relative_to(vault)}; {audio_evidence}; "
                "scratch vault removed after check"
            )
            print(f"\nFILE-BACKED RECORD: PASS ({evidence})")
            return True, evidence
    except Exception as exc:  # prototype: surface a compact failure, then exit non-zero
        evidence = str(exc)
        print(f"\nFILE-BACKED RECORD: FAIL ({evidence})")
        return False, evidence


def interactive_loop() -> None:
    record = RecordState()
    render("initialise", record)
    print("\nCommands: text <value> | audio <ref> | transcript <value> | ai <value> | sync | q")
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if line in {"q", "quit", "exit"}:
            break
        if not line:
            continue
        command, _, value = line.partition(" ")
        mapping = {
            "text": "capture_text",
            "audio": "capture_audio",
            "transcript": "capture_transcript",
            "ai": "append_ai",
        }
        if command == "sync":
            apply_action(record, "sync_to_mac")
        elif command in mapping and value:
            apply_action(record, mapping[command], value)
        else:
            print("unknown command or missing value")
            continue
        render(command, record)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true", help="drive the in-memory state by hand")
    parser.add_argument("--strict", action="store_true", help="fail when manual-only checks remain")
    args = parser.parse_args()

    if args.interactive:
        interactive_loop()
        return 0

    checks = inspect_mac()
    print("=== MAC CAPABILITY PROBE (read-only) ===")
    for check in checks:
        print(f"[{check.status:<6}] {check.name}: {check.evidence}")

    record_passed = run_record_scenario()
    file_backed_passed, file_backed_evidence = run_file_backed_scenario()
    failures = [check for check in checks if check.status == "FAIL"]
    manual = [check for check in checks if check.status == "MANUAL"]
    print("\n=== SUMMARY ===")
    print(json.dumps({
        "local_failures": [check.name for check in failures],
        "manual_or_device_checks": [check.name for check in manual],
        "record_contract": "PASS" if record_passed else "FAIL",
        "file_backed_record": "PASS" if file_backed_passed else "FAIL",
        "file_backed_evidence": file_backed_evidence,
        "side_effects": "none: scratch vault only; no real vault, shortcut, recording, or note was modified",
    }, ensure_ascii=False, indent=2))

    if failures or not record_passed or not file_backed_passed:
        return 1
    if args.strict and manual:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
