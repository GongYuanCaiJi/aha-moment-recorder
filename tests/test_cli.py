from __future__ import annotations

import io
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from aha_moment_recorder.cli import main
from aha_moment_recorder.config import load_settings


class FakeLaunchctl:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.print_calls = 0

    def __call__(self, args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[:2] == ["launchctl", "print"]:
            self.print_calls += 1
            if self.print_calls == 1:
                return subprocess.CompletedProcess(args, 113, stdout="", stderr="Could not find service")
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="state = running\nlast exit code = 0\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class CliTests(unittest.TestCase):
    def test_init_writes_config_and_creates_vault_and_source_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "settings.toml"
            vault = root / "vault"
            inbox = root / "inbox"
            output = io.StringIO()

            with redirect_stdout(output):
                result = main(
                    [
                        "init",
                        "--config",
                        str(config),
                        "--vault",
                        str(vault),
                        "--source",
                        str(inbox),
                        "--endpoint",
                        "https://provider.example/v1",
                    ],
                    platform="darwin",
                )

            self.assertEqual(result, 0)
            self.assertTrue(config.is_file())
            self.assertTrue((vault / "records").is_dir())
            self.assertTrue(inbox.is_dir())
            self.assertTrue((vault / ".bridge/state.json").is_file())
            self.assertNotIn("api_key =", config.read_text(encoding="utf-8"))
            settings = load_settings(config, env={}, cwd=root)
            self.assertEqual(settings.vault, vault.resolve())
            self.assertEqual(settings.sources, (inbox.resolve(),))
            self.assertEqual(settings.endpoint, "https://provider.example/v1")
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["status"], "initialized")
            self.assertEqual(payload["config"], str(config.resolve()))

    def test_doctor_reports_configuration_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "settings.toml"
            vault = root / "vault"
            inbox = root / "inbox"
            vault.mkdir()
            inbox.mkdir()
            config.write_text(
                "\n".join(
                    [
                        "[aha_moment_recorder]",
                        f'vault = "{vault}"',
                        f'sources = ["{inbox}"]',
                        'endpoint = "https://provider.example/v1"',
                        'model = "test-model"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            output = io.StringIO()

            with redirect_stdout(output):
                result = main(
                    [
                        "doctor",
                        "--config",
                        str(config),
                        "--agent-path",
                        str(root / "agent.plist"),
                    ],
                    platform="darwin",
                )

            self.assertEqual(result, 0)
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["vault"]["exists"])
            self.assertTrue(payload["sources"][0]["exists"])
            self.assertEqual(payload["api_key"], "not configured")
            self.assertNotIn("fixture-secret", output.getvalue())

    def test_install_agent_cli_uses_injected_runner_and_reports_log_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "settings.toml"
            vault = root / "vault"
            inbox = root / "inbox"
            vault.mkdir()
            inbox.mkdir()
            config.write_text(
                "\n".join(
                    [
                        "[aha_moment_recorder]",
                        f'vault = "{vault}"',
                        f'sources = ["{inbox}"]',
                        'endpoint = "https://provider.example/v1"',
                        'model = "test-model"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            agent_path = root / "LaunchAgents/com.aha-moment-recorder.plist"
            runner = FakeLaunchctl()
            output = io.StringIO()

            with redirect_stdout(output):
                result = main(
                    [
                        "install-agent",
                        "--config",
                        str(config),
                        "--agent-path",
                        str(agent_path),
                    ],
                    launchctl_runner=runner,
                    platform="darwin",
                )

            self.assertEqual(result, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["status"], "installed")
            self.assertTrue(payload["launch_agent"]["loaded"])
            self.assertEqual(
                payload["stdout_path"],
                str((vault / ".bridge/launchagent.stdout.log").resolve()),
            )
            plist = plistlib.loads(agent_path.read_bytes())
            self.assertEqual(plist["ProgramArguments"][-2:], ["--config", str(config.resolve())])
            self.assertIn(
                ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(agent_path.resolve())],
                runner.calls,
            )

    def test_doctor_reports_loaded_agent_and_last_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / "settings.toml"
            vault = root / "vault"
            inbox = root / "inbox"
            stdout_path = root / "stdout.log"
            stderr_path = root / "stderr.log"
            vault.mkdir()
            inbox.mkdir()
            config.write_text(
                "\n".join(
                    [
                        "[aha_moment_recorder]",
                        f'vault = "{vault}"',
                        f'sources = ["{inbox}"]',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            agent_path = root / "agent.plist"
            agent_path.write_bytes(
                plistlib.dumps(
                    {
                        "Label": "com.aha-moment-recorder",
                        "ProgramArguments": ["/usr/bin/python3", "-m", "aha_moment_recorder", "watch"],
                        "WorkingDirectory": str(vault.resolve()),
                        "RunAtLoad": True,
                        "KeepAlive": True,
                        "StandardOutPath": str(stdout_path.resolve()),
                        "StandardErrorPath": str(stderr_path.resolve()),
                    }
                )
            )

            def runner(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(
                    args,
                    0,
                    stdout="state = running\nlast exit code = 0\n",
                    stderr="",
                )

            output = io.StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "doctor",
                        "--config",
                        str(config),
                        "--agent-path",
                        str(agent_path),
                    ],
                    launchctl_runner=runner,
                    platform="darwin",
                )

            self.assertEqual(result, 0)
            payload = json.loads(output.getvalue())
            self.assertTrue(payload["launch_agent"]["loaded"])
            self.assertTrue(payload["launch_agent"]["running"])
            self.assertEqual(payload["launch_agent"]["last_exit"], 0)
            self.assertFalse(payload["launch_agent"]["stdout_exists"])


if __name__ == "__main__":
    unittest.main()
