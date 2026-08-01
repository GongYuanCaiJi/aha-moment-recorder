"""Git commit adapter with path-scoped, injectable command execution."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Sequence


class GitCommitError(RuntimeError):
    """Raised when a target record could not be committed."""


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class GitCommitter:
    def __init__(
        self,
        vault: Path,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.vault = Path(vault).expanduser().resolve()
        self.runner = runner or subprocess.run

    def _run(self, args: Sequence[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if callable(self.runner):
            return self.runner(list(args), **kwargs)
        return self.runner.run(list(args), **kwargs)  # type: ignore[attr-defined]

    def _worktree_root(self) -> Path | None:
        try:
            result = self._run(
                ["git", "-C", str(self.vault), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return Path(result.stdout.strip()).expanduser().resolve()

    def commit(self, record_path: Path, record_id: str, state_path: Path | None = None) -> str | None:
        root = self._worktree_root()
        if root is None or root != self.vault:
            return None
        try:
            record_relative = Path(record_path).resolve().parent.relative_to(root)
        except ValueError as exc:
            raise GitCommitError("record path is outside the Vault worktree") from exc
        target_paths = [record_relative.as_posix()]
        if state_path is not None:
            try:
                state_relative = Path(state_path).resolve().relative_to(root)
            except ValueError:
                state_relative = None
            if state_relative is not None and state_relative.as_posix() not in target_paths:
                target_paths.append(state_relative.as_posix())

        add_result = self._run(
            ["git", "-C", str(root), "add", "--", *target_paths],
            capture_output=True,
            text=True,
            check=False,
        )
        if add_result.returncode != 0:
            raise GitCommitError("git add failed")

        status_result = self._run(
            [
                "git",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *target_paths,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if status_result.returncode != 0:
            raise GitCommitError("git status failed")
        if not status_result.stdout.strip():
            return None

        commit_result = self._run(
            [
                "git",
                "-C",
                str(root),
                "commit",
                "--only",
                "-m",
                f"record: update {record_id}",
                "--",
                *target_paths,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if commit_result.returncode != 0:
            raise GitCommitError("git commit failed")
        output = commit_result.stdout.strip()
        return output.splitlines()[-1] if output else "committed"
