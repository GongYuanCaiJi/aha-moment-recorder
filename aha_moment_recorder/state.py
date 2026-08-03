"""Machine-readable state with atomic writes and rollback snapshots."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class StateStore:
    def __init__(self, path: Path, *, clock: Callable[[], str] = utc_now) -> None:
        self.path = Path(path).expanduser().resolve()
        self.clock = clock
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "groups": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "groups": {}}
        if not isinstance(value, dict) or not isinstance(value.get("groups", {}), dict):
            return {"version": 1, "groups": {}}
        value.setdefault("version", 1)
        return value

    def get(self, record_id: str) -> dict[str, Any] | None:
        value = self.data.setdefault("groups", {}).get(record_id)
        return dict(value) if isinstance(value, Mapping) else None

    def set(self, record_id: str, value: Mapping[str, Any]) -> None:
        self.data.setdefault("groups", {})[record_id] = dict(value)

    def remove(self, record_id: str) -> None:
        self.data.setdefault("groups", {}).pop(record_id, None)

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.data)

    def restore(self, snapshot: Mapping[str, Any]) -> None:
        self.data = copy.deepcopy(dict(snapshot))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".part",
            mode="w",
            encoding="utf-8",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)
