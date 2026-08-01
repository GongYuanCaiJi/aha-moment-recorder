from __future__ import annotations

import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from aha_moment_recorder.launchagent import LaunchAgentManager


class FakeLaunchctl:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.print_calls = 0

    def __call__(self, args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ["launchctl", "print"]:
            self.print_calls += 1
            if self.print_calls == 1:
                return subprocess.CompletedProcess(
                    args,
                    113,
                    stdout="",
                    stderr="Could not find service",
                )
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="state = running\nlast exit code = 0\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class LaunchAgentTests(unittest.TestCase):
    def test_install_validates_plist_and_runs_real_lifecycle_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "LaunchAgents/com.aha-moment-recorder.plist"
            stdout_path = root / "logs/stdout.log"
            stderr_path = root / "logs/stderr.log"
            runner = FakeLaunchctl()
            manager = LaunchAgentManager(
                path,
                uid=501,
                runner=runner,
                platform="darwin",
            )

            status = manager.install(
                ["/usr/bin/python3", "-m", "aha_moment_recorder", "watch"],
                working_directory=root,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )

            payload = plistlib.loads(path.read_bytes())
            self.assertEqual(payload["Label"], "com.aha-moment-recorder")
            self.assertEqual(payload["ProgramArguments"][0], "/usr/bin/python3")
            self.assertEqual(payload["WorkingDirectory"], str(root.resolve()))
            self.assertEqual(payload["StandardOutPath"], str(stdout_path.resolve()))
            self.assertEqual(payload["StandardErrorPath"], str(stderr_path.resolve()))
            self.assertEqual(status.loaded, True)
            self.assertEqual(status.running, True)
            self.assertEqual(status.last_exit, 0)
            self.assertIn(
                ["plutil", "-lint", str(path.resolve())],
                runner.calls,
            )
            self.assertIn(
                ["launchctl", "bootstrap", "gui/501", str(path.resolve())],
                runner.calls,
            )
            self.assertIn(
                ["launchctl", "kickstart", "-k", "gui/501/com.aha-moment-recorder"],
                runner.calls,
            )

    def test_status_parses_not_running_and_last_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args,
                    0,
                    stdout="state = not running\nlast exit code = 42\n",
                    stderr="",
                )

            status = LaunchAgentManager(
                root / "agent.plist",
                uid=501,
                runner=runner,
                platform="darwin",
            ).status()

            self.assertTrue(status.loaded)
            self.assertFalse(status.running)
            self.assertEqual(status.last_exit, 42)
            self.assertFalse(status.last_exit_success)

    def test_uninstall_boots_out_before_removing_plist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "agent.plist"
            path.write_bytes(plistlib.dumps({"Label": "com.aha-moment-recorder"}))
            runner = FakeLaunchctl()

            status = LaunchAgentManager(
                path,
                uid=501,
                runner=runner,
                platform="darwin",
            ).uninstall()

            self.assertFalse(path.exists())
            self.assertEqual(status["status"], "uninstalled")
            self.assertEqual(
                runner.calls,
                [["launchctl", "bootout", "gui/501", str(path.resolve())]],
            )


if __name__ == "__main__":
    unittest.main()
