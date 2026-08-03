"""Safe, observable macOS LaunchAgent lifecycle for the CLI."""

from __future__ import annotations

from dataclasses import dataclass
import os
import plistlib
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


DEFAULT_LABEL = "com.aha-moment-recorder"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class LaunchAgentError(RuntimeError):
    """Raised when a LaunchAgent cannot be validated or managed."""


@dataclass(frozen=True)
class LaunchAgentStatus:
    label: str
    plist_path: Path
    stdout_path: Path | None
    stderr_path: Path | None
    domain: str
    loaded: bool
    running: bool | None
    last_exit: int | None
    detail: str | None = None

    @property
    def last_exit_success(self) -> bool | None:
        if self.last_exit is None:
            return None
        return self.last_exit == 0

    @property
    def last_exit_code(self) -> int | None:
        """Compatibility spelling for callers that mirror launchctl output."""

        return self.last_exit

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "plist_path": str(self.plist_path),
            "stdout_path": str(self.stdout_path) if self.stdout_path else None,
            "stderr_path": str(self.stderr_path) if self.stderr_path else None,
            "domain": self.domain,
            "loaded": self.loaded,
            "running": self.running,
            "last_exit": self.last_exit,
            "last_exit_code": self.last_exit_code,
            "last_exit_success": self.last_exit_success,
            **({"detail": self.detail} if self.detail else {}),
        }


def _string_path(value: object, *, field_name: str) -> str:
    if not isinstance(value, (str, Path)) or not str(value):
        raise LaunchAgentError(f"{field_name} must be a non-empty path")
    return str(Path(value).expanduser().resolve())


def build_launch_agent_plist(
    *,
    label: str,
    program_arguments: Sequence[str],
    working_directory: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, object]:
    """Build the user-specific plist payload without embedding secrets."""

    if not label or not program_arguments or any(not isinstance(item, str) or not item for item in program_arguments):
        raise LaunchAgentError("LaunchAgent label and ProgramArguments are required")
    payload: dict[str, object] = {
        "Label": label,
        "ProgramArguments": list(program_arguments),
        "WorkingDirectory": _string_path(working_directory, field_name="WorkingDirectory"),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": _string_path(stdout_path, field_name="StandardOutPath"),
        "StandardErrorPath": _string_path(stderr_path, field_name="StandardErrorPath"),
    }
    validate_launch_agent_plist(payload)
    return payload


def validate_launch_agent_plist(payload: Mapping[str, object]) -> None:
    """Validate the fields launchd needs before a bootstrap attempt."""

    required = {
        "Label",
        "ProgramArguments",
        "WorkingDirectory",
        "StandardOutPath",
        "StandardErrorPath",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise LaunchAgentError(f"LaunchAgent plist is missing: {', '.join(missing)}")
    if not isinstance(payload["Label"], str) or not payload["Label"]:
        raise LaunchAgentError("LaunchAgent Label must be a non-empty string")
    arguments = payload["ProgramArguments"]
    if not isinstance(arguments, list) or not arguments or not all(isinstance(item, str) and item for item in arguments):
        raise LaunchAgentError("LaunchAgent ProgramArguments must be a non-empty string array")
    for field_name in ("WorkingDirectory", "StandardOutPath", "StandardErrorPath"):
        if not isinstance(payload[field_name], str) or not payload[field_name]:
            raise LaunchAgentError(f"LaunchAgent {field_name} must be a non-empty string")


def render_launch_agent_plist(payload: Mapping[str, object]) -> bytes:
    """Serialize and round-trip a plist so malformed output fails early."""

    validate_launch_agent_plist(payload)
    rendered = plistlib.dumps(dict(payload), fmt=plistlib.FMT_XML, sort_keys=True)
    try:
        decoded = plistlib.loads(rendered)
    except plistlib.InvalidFileException as exc:
        raise LaunchAgentError("generated LaunchAgent plist is invalid") from exc
    validate_launch_agent_plist(decoded)
    return rendered


_STATE_RE = re.compile(r"^\s*state\s*=\s*(\S+)", re.MULTILINE)
_PID_RE = re.compile(r"^\s*pid\s*=\s*(\d+)", re.MULTILINE)
_LAST_EXIT_RE = re.compile(r"last exit code\s*=\s*(-?\d+)", re.IGNORECASE)
_ABSENT_MARKERS = (
    "could not find service",
    "no such process",
    "service not found",
    "unknown service",
)


class LaunchAgentManager:
    """Manage one user LaunchAgent with an injectable process boundary."""

    def __init__(
        self,
        plist_path: Path,
        *,
        label: str = DEFAULT_LABEL,
        uid: int | None = None,
        runner: CommandRunner | None = None,
        platform: str | None = None,
    ) -> None:
        self.plist_path = Path(plist_path).expanduser().resolve()
        self.label = label
        self.uid = os.getuid() if uid is None else uid
        self.runner = runner or subprocess.run
        self.platform = sys.platform if platform is None else platform

    @property
    def domain(self) -> str:
        return f"gui/{self.uid}"

    @property
    def target(self) -> str:
        return f"{self.domain}/{self.label}"

    def _require_macos(self) -> None:
        if self.platform != "darwin":
            raise LaunchAgentError("LaunchAgent commands require macOS")

    def _run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(
                list(arguments),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise LaunchAgentError(f"cannot execute {arguments[0]}: {exc}") from exc

    @staticmethod
    def _output(result: subprocess.CompletedProcess[str]) -> str:
        return "\n".join(
            value.strip()
            for value in (getattr(result, "stdout", ""), getattr(result, "stderr", ""))
            if value and value.strip()
        )

    @staticmethod
    def _is_absent(result: subprocess.CompletedProcess[str]) -> bool:
        output = LaunchAgentManager._output(result).lower()
        return any(marker in output for marker in _ABSENT_MARKERS)

    def _check_success(self, result: subprocess.CompletedProcess[str], command: str) -> None:
        if result.returncode == 0:
            return
        detail = self._output(result) or f"exit code {result.returncode}"
        raise LaunchAgentError(f"{command} failed: {detail}")

    def _plist_paths(self) -> tuple[Path | None, Path | None, str | None]:
        if not self.plist_path.is_file():
            return None, None, None
        try:
            payload = plistlib.loads(self.plist_path.read_bytes())
            validate_launch_agent_plist(payload)
        except (OSError, plistlib.InvalidFileException, LaunchAgentError) as exc:
            return None, None, str(exc)
        stdout = payload.get("StandardOutPath")
        stderr = payload.get("StandardErrorPath")
        return (
            Path(stdout) if isinstance(stdout, str) else None,
            Path(stderr) if isinstance(stderr, str) else None,
            None,
        )

    def _assert_owned_plist(self) -> None:
        """Refuse to overwrite or remove a plist owned by another label."""

        if not self.plist_path.is_file():
            return
        try:
            payload = plistlib.loads(self.plist_path.read_bytes())
        except (OSError, plistlib.InvalidFileException) as exc:
            raise LaunchAgentError(f"cannot manage invalid LaunchAgent plist: {self.plist_path}") from exc
        if not isinstance(payload, Mapping) or payload.get("Label") != self.label:
            actual = payload.get("Label") if isinstance(payload, Mapping) else None
            raise LaunchAgentError(
                f"LaunchAgent plist label mismatch: expected {self.label}, got {actual}"
            )

    def status(self) -> LaunchAgentStatus:
        self._require_macos()
        result = self._run(["launchctl", "print", self.target])
        output = self._output(result)
        loaded = result.returncode == 0
        state_match = _STATE_RE.search(output)
        pid_match = _PID_RE.search(output)
        running: bool | None = None
        if state_match:
            running = state_match.group(1).lower() == "running"
        elif pid_match:
            running = int(pid_match.group(1)) > 0
        last_exit_match = _LAST_EXIT_RE.search(output)
        last_exit = int(last_exit_match.group(1)) if last_exit_match else None
        stdout_path, stderr_path, plist_detail = self._plist_paths()
        detail = None
        if not loaded:
            detail = output or "service is not loaded"
        elif plist_detail:
            detail = plist_detail
        return LaunchAgentStatus(
            label=self.label,
            plist_path=self.plist_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            domain=self.domain,
            loaded=loaded,
            running=running,
            last_exit=last_exit,
            detail=detail,
        )

    def install(
        self,
        program_arguments: Sequence[str],
        *,
        working_directory: Path,
        stdout_path: Path,
        stderr_path: Path,
    ) -> LaunchAgentStatus:
        self._require_macos()
        self._assert_owned_plist()
        payload = build_launch_agent_plist(
            label=self.label,
            program_arguments=program_arguments,
            working_directory=working_directory,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )
        rendered = render_launch_agent_plist(payload)
        try:
            self.plist_path.parent.mkdir(parents=True, exist_ok=True)
            Path(stdout_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            Path(stderr_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            self.plist_path.write_bytes(rendered)
            self.plist_path.chmod(0o600)
        except OSError as exc:
            raise LaunchAgentError(f"cannot write LaunchAgent files: {exc}") from exc

        lint = self._run(["plutil", "-lint", str(self.plist_path)])
        self._check_success(lint, "plutil -lint")

        previous = self.status()
        if previous.loaded:
            bootout = self._run(["launchctl", "bootout", self.domain, str(self.plist_path)])
            self._check_success(bootout, "launchctl bootout")

        bootstrap = self._run(["launchctl", "bootstrap", self.domain, str(self.plist_path)])
        self._check_success(bootstrap, "launchctl bootstrap")
        kickstart = self._run(["launchctl", "kickstart", "-k", self.target])
        self._check_success(kickstart, "launchctl kickstart")
        status = self.status()
        for _ in range(10):
            if status.running is True or status.last_exit is not None:
                break
            time.sleep(0.1)
            status = self.status()
        return status

    def uninstall(self) -> dict[str, str]:
        self._require_macos()
        self._assert_owned_plist()
        bootout = self._run(["launchctl", "bootout", self.domain, str(self.plist_path)])
        if bootout.returncode != 0 and not self._is_absent(bootout):
            self._check_success(bootout, "launchctl bootout")
        try:
            if self.plist_path.exists():
                self.plist_path.unlink()
        except OSError as exc:
            raise LaunchAgentError(f"cannot remove LaunchAgent plist: {exc}") from exc
        return {"status": "uninstalled", "path": str(self.plist_path)}
