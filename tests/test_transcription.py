from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from aha_moment_recorder.transcription import TranscriptionError, WhisperCppTranscriber


class RecordingRunner:
    def __init__(self, *, write_transcript: bool = True, empty_transcript: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.write_transcript = write_transcript
        self.empty_transcript = empty_transcript

    def __call__(self, args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[0] == "whisper-cli" and self.write_transcript:
            output_base = Path(args[args.index("-of") + 1])
            text = "" if self.empty_transcript else "本機逐字稿\n"
            output_base.with_suffix(".txt").write_text(text, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class TranscriptionTests(unittest.TestCase):
    def test_whisper_cpp_transcriber_converts_audio_and_writes_atomic_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "voice.m4a"
            model = root / "ggml-small.bin"
            output = root / "record/attachments/transcript-01.txt"
            audio.write_bytes(b"fixture audio")
            model.write_bytes(b"fixture model")
            runner = RecordingRunner()

            text = WhisperCppTranscriber(
                model,
                runner=runner,
                timeout=7,
            ).transcribe(audio, output)

            self.assertEqual(text, "本機逐字稿")
            self.assertEqual(output.read_text(encoding="utf-8"), "本機逐字稿\n")
            self.assertEqual([call[0] for call in runner.calls], ["ffmpeg", "whisper-cli"])
            whisper = runner.calls[1]
            self.assertEqual(whisper[whisper.index("-l") + 1], "zh")
            self.assertEqual(whisper[whisper.index("-m") + 1], str(model.resolve()))

    def test_missing_model_and_empty_output_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "voice.m4a"
            audio.write_bytes(b"fixture audio")
            with self.assertRaisesRegex(TranscriptionError, "model does not exist"):
                WhisperCppTranscriber(root / "missing.bin").transcribe(audio, root / "out.txt")

            model = root / "ggml-small.bin"
            model.write_bytes(b"fixture model")
            with self.assertRaisesRegex(TranscriptionError, "empty text"):
                WhisperCppTranscriber(
                    model,
                    runner=RecordingRunner(empty_transcript=True),
                ).transcribe(audio, root / "out.txt")


if __name__ == "__main__":
    unittest.main()
