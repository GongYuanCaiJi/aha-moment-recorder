"""Portable core pipeline for the personal record system."""

from .config import ConfigError, Settings, load_settings
from .git_adapter import GitCommitError, GitCommitter
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

__all__ = [
    "ConfigError",
    "FOUR_FIELDS",
    "GitCommitError",
    "GitCommitter",
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
    "load_settings",
    "parse_organization",
    "pipeline_from_settings",
    "source_signature",
]
