"""Command line interface for the portable record pipeline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .config import (
    CAPTURE_ONLY,
    COLLECT_AND_ORGANIZE,
    ConfigError,
    Settings,
    load_settings,
    write_config,
)
from .apple_notes import AppleNotesImportError, AppleNotesScanner
from .launchagent import DEFAULT_LABEL, LaunchAgentError, LaunchAgentManager
from .pipeline import pipeline_from_settings


COMMANDS = ("init", "doctor", "run", "watch", "install-agent", "uninstall-agent")
DEFAULT_AGENT_PATH = Path.home() / "Library/LaunchAgents/com.aha-moment-recorder.plist"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=COMMANDS)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--source", type=Path, action="append", dest="sources", default=None)
    parser.add_argument("--state", type=Path, dest="state_path")
    parser.add_argument("--endpoint", "--proxy-url", dest="endpoint")
    parser.add_argument("--model")
    parser.add_argument("--mode", choices=[CAPTURE_ONLY, COLLECT_AND_ORGANIZE])
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--apple-notes-database", type=Path)
    parser.add_argument("--include-deleted-notes", action="store_true", default=None)
    parser.add_argument("--no-apple-notes", action="store_true", default=None)
    parser.add_argument("--reasoning-effort", dest="reasoning_effort")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--no-git-commit", action="store_true", default=None)
    parser.add_argument("--retry-ai", action="store_true", default=None)
    parser.add_argument("--no-transcribe", action="store_true", default=None)
    parser.add_argument("--stt-command")
    parser.add_argument("--stt-ffmpeg-command")
    parser.add_argument("--stt-model", type=Path)
    parser.add_argument("--stt-language")
    parser.add_argument("--stt-timeout", type=float)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--watch", action="store_true", default=None)
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--after", help="only process source files modified at/after this ISO-8601 time")
    parser.add_argument("--agent-path", type=Path, default=DEFAULT_AGENT_PATH)
    parser.add_argument("--agent-label", default=DEFAULT_LABEL)
    parser.add_argument("--stdout-path", type=Path)
    parser.add_argument("--stderr-path", type=Path)
    parser.add_argument("--force", action="store_true", default=False)
    return parser


def _cli_values(args: argparse.Namespace) -> dict[str, Any]:
    values = vars(args).copy()
    values.pop("command", None)
    values.pop("watch", None)
    values.pop("interval", None)
    values.pop("after", None)
    values.pop("agent_path", None)
    values.pop("stdout_path", None)
    values.pop("stderr_path", None)
    values.pop("force", None)
    values.pop("agent_label", None)
    return {key: value for key, value in values.items() if value is not None}


def _after_epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError as exc:
        raise ConfigError(f"invalid --after timestamp: {exc}") from exc


def _doctor(
    settings: Settings,
    *,
    agent_path: Path = DEFAULT_AGENT_PATH,
    agent_label: str = DEFAULT_LABEL,
    launchctl_runner: Any | None = None,
    platform: str | None = None,
) -> int:
    source_checks = [
        {
            "path": str(path),
            "exists": path.is_dir(),
            "readable": path.is_dir() and os.access(path, os.R_OK),
        }
        for path in settings.sources
    ]
    checks = {
        "vault": {"path": str(settings.vault), "exists": settings.vault.is_dir()},
        "sources": source_checks,
        "state_parent": {"path": str(settings.state_path.parent), "exists": settings.state_path.parent.is_dir()},
        "endpoint": settings.endpoint,
        "api_key": "configured" if settings.api_key else "not configured",
        "apple_notes": {
            "database": str(settings.apple_notes_database) if settings.apple_notes_database else None,
            "enabled": settings.apple_notes_database is not None,
            "exists": bool(settings.apple_notes_database and settings.apple_notes_database.is_file()),
            "parser_available": AppleNotesScanner.dependency_available(),
            "include_deleted": settings.include_deleted_notes,
        },
        "transcription": {
            "enabled": bool(settings.auto_transcribe and settings.stt_model),
            "auto_transcribe": settings.auto_transcribe,
            "command": settings.stt_command,
            "command_available": bool(shutil.which(settings.stt_command)),
            "ffmpeg_command": settings.stt_ffmpeg_command,
            "ffmpeg_available": bool(shutil.which(settings.stt_ffmpeg_command)),
            "model": str(settings.stt_model) if settings.stt_model else None,
            "model_exists": bool(settings.stt_model and settings.stt_model.is_file()),
            "language": settings.stt_language,
        },
    }
    actual_platform = sys.platform if platform is None else platform
    if actual_platform == "darwin":
        agent = {"configured": agent_path.is_file(), "plist_path": str(agent_path)}
        if agent_path.is_file():
            status = LaunchAgentManager(
                agent_path,
                runner=launchctl_runner,
                platform=actual_platform,
                label=agent_label,
            ).status()
            agent.update(status.as_dict())
            agent["stdout_exists"] = bool(status.stdout_path and status.stdout_path.exists())
            agent["stderr_exists"] = bool(status.stderr_path and status.stderr_path.exists())
        checks["launch_agent"] = agent
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    healthy = checks["vault"]["exists"] and all(item["exists"] for item in source_checks)
    transcription = checks["transcription"]
    if transcription["enabled"]:
        healthy = (
            healthy
            and bool(transcription["command_available"])
            and bool(transcription["ffmpeg_available"])
            and bool(transcription["model_exists"])
        )
    agent = checks.get("launch_agent")
    if isinstance(agent, dict) and agent.get("configured"):
        healthy = (
            healthy
            and bool(agent.get("loaded"))
            and bool(agent.get("running"))
            and agent.get("last_exit_success") is not False
            and not agent.get("detail")
        )
    return 0 if healthy else 1


def _init(settings: Settings, *, config_path: Path | None = None, force: bool = False) -> int:
    config_target = config_path.expanduser().resolve() if config_path else None
    if config_target is not None and (force or not config_target.exists()):
        write_config(config_target, settings, overwrite=force)
    settings.vault.mkdir(parents=True, exist_ok=True)
    (settings.vault / "records").mkdir(exist_ok=True)
    for source in settings.sources:
        source.mkdir(parents=True, exist_ok=True)
    settings.state_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings.state_path.exists():
        from .state import StateStore

        StateStore(settings.state_path).save()
    print(
        json.dumps(
            {
                "status": "initialized",
                "config": str(config_target) if config_target else None,
                "vault": str(settings.vault),
                "sources": [str(path) for path in settings.sources],
                "state": str(settings.state_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _agent_command(settings: Settings) -> list[str]:
    command = [sys.executable, "-m", "aha_moment_recorder", "watch"]
    if settings.config_path:
        command.extend(["--config", str(settings.config_path)])
        # A CLI override must survive the hand-off to launchd; shell
        # environment variables are not reliably inherited by LaunchAgents.
        if settings.api_key_file:
            command.extend(["--api-key-file", str(settings.api_key_file)])
    else:
        command.extend(
            [
                "--vault",
                str(settings.vault),
                "--state",
                str(settings.state_path),
                "--endpoint",
                settings.endpoint,
                "--model",
                settings.model,
                "--mode",
                settings.mode,
                "--reasoning-effort",
                settings.reasoning_effort,
                "--timeout",
                str(settings.timeout),
            ]
        )
        for source in settings.sources:
            command.extend(["--source", str(source)])
        if settings.apple_notes_database is not None:
            command.extend(["--apple-notes-database", str(settings.apple_notes_database)])
        if settings.include_deleted_notes:
            command.append("--include-deleted-notes")
        if settings.api_key_file:
            command.extend(["--api-key-file", str(settings.api_key_file)])
        if not settings.auto_commit:
            command.append("--no-git-commit")
        if settings.retry_ai:
            command.append("--retry-ai")
        if not settings.auto_transcribe:
            command.append("--no-transcribe")
        if settings.stt_command != "whisper-cli":
            command.extend(["--stt-command", settings.stt_command])
        if settings.stt_ffmpeg_command != "ffmpeg":
            command.extend(["--stt-ffmpeg-command", settings.stt_ffmpeg_command])
        if settings.stt_model is not None:
            command.extend(["--stt-model", str(settings.stt_model)])
        if settings.stt_language != "zh":
            command.extend(["--stt-language", settings.stt_language])
        if settings.stt_timeout != 300.0:
            command.extend(["--stt-timeout", str(settings.stt_timeout)])
        if settings.dry_run:
            command.append("--dry-run")
    return command


def _install_agent(
    settings: Settings,
    path: Path,
    *,
    label: str = DEFAULT_LABEL,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    launchctl_runner: Any | None = None,
    platform: str | None = None,
) -> int:
    actual_platform = sys.platform if platform is None else platform
    if actual_platform != "darwin":
        print("install-agent requires macOS", file=sys.stderr)
        return 1
    stdout_target = stdout_path or settings.vault / ".bridge/launchagent.stdout.log"
    stderr_target = stderr_path or settings.vault / ".bridge/launchagent.stderr.log"
    manager = LaunchAgentManager(
        path,
        label=label,
        runner=launchctl_runner,
        platform=actual_platform,
    )
    status = manager.install(
        _agent_command(settings),
        working_directory=settings.vault,
        stdout_path=stdout_target,
        stderr_path=stderr_target,
    )
    payload = {
        "status": "installed",
        "path": str(path.expanduser().resolve()),
        "stdout_path": str(stdout_target.expanduser().resolve()),
        "stderr_path": str(stderr_target.expanduser().resolve()),
        "launch_agent": status.as_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if status.loaded and status.running is True and status.last_exit_success is not False else 1


def _uninstall_agent(
    path: Path,
    *,
    label: str = DEFAULT_LABEL,
    launchctl_runner: Any | None = None,
    platform: str | None = None,
) -> int:
    manager = LaunchAgentManager(
        path,
        label=label,
        runner=launchctl_runner,
        platform=sys.platform if platform is None else platform,
    )
    print(json.dumps(manager.uninstall(), ensure_ascii=False))
    return 0


def _load_settings_for_command(args: argparse.Namespace, values: dict[str, Any]) -> Settings:
    if args.command == "init" and args.config is not None and not args.config.expanduser().exists():
        values = values.copy()
        values.pop("config", None)
    return load_settings(cli=values)


def main(
    argv: Sequence[str] | None = None,
    *,
    launchctl_runner: Any | None = None,
    platform: str | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = _load_settings_for_command(args, _cli_values(args))
        if args.command == "init":
            return _init(settings, config_path=args.config, force=args.force)
        if args.command == "doctor":
            return _doctor(
                settings,
                agent_path=args.agent_path,
                agent_label=args.agent_label,
                launchctl_runner=launchctl_runner,
                platform=platform,
            )
        if args.command == "install-agent":
            return _install_agent(
                settings,
                args.agent_path,
                label=args.agent_label,
                stdout_path=args.stdout_path,
                stderr_path=args.stderr_path,
                launchctl_runner=launchctl_runner,
                platform=platform,
            )
        if args.command == "uninstall-agent":
            return _uninstall_agent(
                args.agent_path,
                label=args.agent_label,
                launchctl_runner=launchctl_runner,
                platform=platform,
            )
        pipeline = pipeline_from_settings(settings)
        after_epoch = _after_epoch(args.after)
        if after_epoch is not None:
            pipeline.scanner.after_epoch = after_epoch
        if args.command == "watch" or args.watch:
            pipeline.watch(args.interval)
            return 0
        results = pipeline.scan()
        print(json.dumps({"vault": str(settings.vault), "results": results}, ensure_ascii=False, indent=2))
        return 0 if all(item.get("status") != "error" for item in results) else 1
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except AppleNotesImportError as exc:
        print(f"Apple Notes import error: {exc}", file=sys.stderr)
        return 1
    except LaunchAgentError as exc:
        print(f"launch agent error: {exc}", file=sys.stderr)
        return 1
