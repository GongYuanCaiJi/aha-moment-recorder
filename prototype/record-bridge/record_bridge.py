#!/usr/bin/env python3
"""Compatibility entrypoint for the portable ``aha_moment_recorder`` package."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aha_moment_recorder.cli import build_parser, main  # noqa: E402
from aha_moment_recorder.compat import (  # noqa: E402
    AUDIO_SUFFIXES,
    ATTACHMENT_SUFFIXES,
    DEFAULT_INBOX,
    DEFAULT_MODEL,
    DEFAULT_PROXY_URL,
    DEFAULT_VAULT,
    DEFAULT_VOICE_MEMOS,
    IGNORED_NAMES,
    TEXT_SUFFIXES,
    Bridge,
    RecordGroup,
    extract_frontmatter,
    parse_ai_section,
    parse_json_response,
    render_structured,
    safe_copy,
    source_groups,
    source_signature,
    yaml_value,
)


if __name__ == "__main__":
    raise SystemExit(main())
