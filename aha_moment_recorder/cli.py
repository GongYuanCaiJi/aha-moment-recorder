"""Command line interface for the portable record pipeline."""

from __future__ import annotations

import argparse
import json
import plistlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from .config import ConfigError, Settings, load_settings
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
    parser.add_argument("--mode", choices=["capture-only", "collect-and-organize"])
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--reasoning-effort", dest="reasoning_effort")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--no-git-commit", action="store_true", default=None)
    parser.add_argument("--retry-ai", action="store_true", default=None)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--watch", action="store_true", default=None)
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--after", help="only process source files modified at/after this ISO-8601 time")
    parser.add_argument("--agent-path", type=Path, default=DEFAULT_AGENT_PATH)
    return parser


def _cli_values(args: argparse.Namespace) -> dict[str, Any]:
    values = vars(args).copy()
    values.pop("command", None)
    values.pop("watch", None)
    values.pop("interval", None)
    values.pop("after", None)
    values.pop("agent_path", None)
    return {key: value for key, value in values.items() if value is not None}


def _after_epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError as exc:
        raise ConfigError(f"invalid --after timestamp: {exc}") from exc


def _doctor(settings: Settings) -> int:
    source_checks = [
        {"path": str(path), "exists": path.is_dir(), "readable": path.is_dir() and path.exists()}
        for path in settings.sources
    ]
    checks = {
        "vault": {"path": str(settings.vault), "exists": settings.vault.is_dir()},
        "sources": source_checks,
        "state_parent": {"path": str(settings.state_path.parent), "exists": settings.state_path.parent.is_dir()},
        "endpoint": settings.endpoint,
        "api_key": "configured" if settings.api_key else "not configured",
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 0 if checks["vault"]["exists"] and all(item["exists"] for item in source_checks) else 1


def _init(settings: Settings) -> int:
    settings.vault.mkdir(parents=True, exist_ok=True)
    (settings.vault / "records").mkdir(exist_ok=True)
    settings.state_path.parent.mkdir(parents=True, exist_ok=True)
    if not settings.state_path.exists():
        from .state import StateStore

        StateStore(settings.state_path).save()
    print(json.dumps({"status": "initialized", "vault": str(settings.vault)}, ensure_ascii=False))
    return 0


def _install_agent(settings: Settings, path: Path) -> int:
    if sys.platform != "darwin":
        print("install-agent requires macOS", file=sys.stderr)
        return 1
    command = [sys.executable, "-m", "aha_moment_recorder", "watch"]
    if settings.config_path:
        command.extend(["--config", str(settings.config_path)])
    else:
        command.extend(["--vault", str(settings.vault), "--endpoint", settings.endpoint, "--model", settings.model])
        for source in settings.sources:
            command.extend(["--source", str(source)])
    payload = {
        "Label": "com.aha-moment-recorder",
        "ProgramArguments": command,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": "/tmp/aha-moment-recorder.log",
        "StandardErrorPath": "/tmp/aha-moment-recorder.error.log",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=True))
    print(json.dumps({"status": "installed", "path": str(path)}, ensure_ascii=False))
    return 0


def _uninstall_agent(path: Path) -> int:
    if path.exists():
        path.unlink()
    print(json.dumps({"status": "uninstalled", "path": str(path)}, ensure_ascii=False))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(cli=_cli_values(args))
        if args.command == "init":
            return _init(settings)
        if args.command == "doctor":
            return _doctor(settings)
        if args.command == "install-agent":
            return _install_agent(settings, args.agent_path)
        if args.command == "uninstall-agent":
            return _uninstall_agent(args.agent_path)
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
