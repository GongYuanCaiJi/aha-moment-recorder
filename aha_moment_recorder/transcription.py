"""Pluggable local speech-to-text adapters.

The record pipeline deliberately keeps transcription separate from the
OpenAI-compatible text organizer.  This lets a text-only reverse proxy keep
serving ``gpt-5.6-luna`` while audio is handled by a local or dedicated STT
service.
"""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol


class TranscriptionError(RuntimeError):
    """Raised when an audio file cannot be converted into a transcript."""


class Transcriber(Protocol):
    """Minimal boundary used by :class:`RecordPipeline`."""

    def transcribe(self, audio_path: Path, output_path: Path) -> str: ...


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class WhisperCppTranscriber:
    """Run the local ``whisper-cli`` binary without sending audio to a proxy.

    ``whisper-cli`` accepts PCM WAV, while iPhone Voice Memos normally produce
    m4a.  ffmpeg is therefore used only as a temporary, local format adapter;
    the original audio is never changed.
    """

    def __init__(
        self,
        model: Path,
        *,
        command: str = "whisper-cli",
        ffmpeg_command: str = "ffmpeg",
        language: str = "zh",
        timeout: float = 300.0,
        runner: CommandRunner | None = None,
    ) -> None:
        self.model = Path(model).expanduser().resolve()
        self.command = command
        self.ffmpeg_command = ffmpeg_command
        self.language = language
        self.timeout = timeout
        self.runner = runner or subprocess.run

    def _run(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            result = self.runner(
                list(args),
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise TranscriptionError(f"transcription command not found: {args[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise TranscriptionError(f"transcription timed out after {self.timeout:g}s") from exc
        except OSError as exc:
            raise TranscriptionError(f"transcription command failed: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            message = detail[-1][:240] if detail else f"exit status {result.returncode}"
            raise TranscriptionError(f"transcription command failed: {message}")
        return result

    def transcribe(self, audio_path: Path, output_path: Path) -> str:
        audio = Path(audio_path).expanduser().resolve()
        destination = Path(output_path).expanduser().resolve()
        if not audio.is_file():
            raise TranscriptionError(f"audio file does not exist: {audio}")
        if not self.model.is_file():
            raise TranscriptionError(f"Whisper model does not exist: {self.model}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="aha-moment-transcription-") as temp_dir:
            wav = Path(temp_dir) / "input.wav"
            self._run(
                [
                    self.ffmpeg_command,
                    "-y",
                    "-v",
                    "error",
                    "-i",
                    str(audio),
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    "-c:a",
                    "pcm_s16le",
                    str(wav),
                ]
            )
            output_base = Path(temp_dir) / "transcript"
            self._run(
                [
                    self.command,
                    "-m",
                    str(self.model),
                    "-f",
                    str(wav),
                    "-l",
                    self.language,
                    "-otxt",
                    "-of",
                    str(output_base),
                    "-np",
                    "-nt",
                ]
            )
            generated = Path(f"{output_base}.txt")
            try:
                text = generated.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise TranscriptionError("whisper-cli did not produce a transcript file") from exc

        if not text:
            raise TranscriptionError("transcription returned empty text")
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(destination)
        return text
