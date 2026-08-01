"""Minimal stdlib-only PEP 517 wheel backend for this small package."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import zipfile


NAME = "aha-moment-recorder"
DIST_NAME = "aha_moment_recorder"
VERSION = "0.1.0"
DIST_INFO = f"{DIST_NAME}-{VERSION}.dist-info"


def _metadata() -> str:
    return "\n".join(
        [
            "Metadata-Version: 2.1",
            f"Name: {NAME}",
            f"Version: {VERSION}",
            "Summary: Portable standard-library core pipeline for personal records",
            "Requires-Python: >=3.11",
            "",
        ]
    )


def _wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: aha-moment-recorder stdlib backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _entry_points() -> str:
    return "[console_scripts]\naha-moment-recorder = aha_moment_recorder.cli:main\n"


def _dist_files() -> dict[str, bytes]:
    return {
        f"{DIST_INFO}/METADATA": _metadata().encode("utf-8"),
        f"{DIST_INFO}/WHEEL": _wheel().encode("utf-8"),
        f"{DIST_INFO}/entry_points.txt": _entry_points().encode("utf-8"),
    }


def _record_line(name: str, content: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
    return f"{name},sha256={digest},{len(content)}"


def get_requires_for_build_wheel(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None) -> str:
    target = Path(metadata_directory) / DIST_INFO
    target.mkdir(parents=True, exist_ok=True)
    for name, content in _dist_files().items():
        (Path(metadata_directory) / name).write_bytes(content)
    return DIST_INFO


def build_wheel(wheel_directory: str, config_settings=None, metadata_directory=None) -> str:
    filename = f"{DIST_NAME}-{VERSION}-py3-none-any.whl"
    target = Path(wheel_directory) / filename
    files: dict[str, bytes] = {}
    source_root = Path(__file__).resolve().parent
    for path in sorted((source_root / "aha_moment_recorder").rglob("*.py")):
        files[path.relative_to(source_root).as_posix()] = path.read_bytes()
    files.update(_dist_files())
    record_name = f"{DIST_INFO}/RECORD"
    record = "\n".join(_record_line(name, content) for name, content in sorted(files.items()))
    files[record_name] = (record + f"\n{record_name},,\n").encode("utf-8")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return filename
