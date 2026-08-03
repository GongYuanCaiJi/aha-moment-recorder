"""Portable core pipeline for the personal record system."""

from .config import ConfigError, Settings, load_settings
from .apple_notes import AppleNotesImportError, AppleNotesScanner
from .git_adapter import GitCommitError, GitCommitter
from .launchagent import LaunchAgentError, LaunchAgentManager, LaunchAgentStatus
from .organization import (
    FOUR_FIELDS,
    Organization,
    OrganizationError,
    OpenAICompatibleOrganizer,
    parse_organization,
)
from .pipeline import RecordPipeline, pipeline_from_settings
from .sources import RecordGroup, SourceMetadata, SourceScanner, source_signature
from .state import StateStore
from .storage import RecordStore
from .transcription import Transcriber, TranscriptionError, WhisperCppTranscriber

__all__ = [
    "ConfigError",
    "AppleNotesImportError",
    "AppleNotesScanner",
    "FOUR_FIELDS",
    "GitCommitError",
    "GitCommitter",
    "LaunchAgentError",
    "LaunchAgentManager",
    "LaunchAgentStatus",
    "Organization",
    "OrganizationError",
    "OpenAICompatibleOrganizer",
    "RecordGroup",
    "RecordPipeline",
    "RecordStore",
    "Settings",
    "SourceMetadata",
    "SourceScanner",
    "StateStore",
    "Transcriber",
    "TranscriptionError",
    "WhisperCppTranscriber",
    "load_settings",
    "parse_organization",
    "pipeline_from_settings",
    "source_signature",
]
