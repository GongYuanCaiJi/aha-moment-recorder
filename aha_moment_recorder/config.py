"""Configuration loading with TOML < environment < CLI precedence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility diagnostic
    tomllib = None  # type: ignore[assignment]


DEFAULT_ENDPOINT = "http://127.0.0.1:8317/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_STT_COMMAND = "whisper-cli"
DEFAULT_STT_FFMPEG_COMMAND = "ffmpeg"
DEFAULT_STT_LANGUAGE = "zh"
DEFAULT_STT_TIMEOUT = 300.0
CAPTURE_ONLY = "capture-only"
COLLECT_AND_ORGANIZE = "collect-and-organize"
ProcessingMode = Literal["capture-only", "collect-and-organize"]
DEFAULT_MODE: ProcessingMode = COLLECT_AND_ORGANIZE
VALID_MODES = frozenset({CAPTURE_ONLY, COLLECT_AND_ORGANIZE})
CONFIG_ENV = "AHA_MOMENT_RECORDER_CONFIG"


class ConfigError(ValueError):
    """Raised when configuration is missing, invalid, or unsafe."""


@dataclass(frozen=True)
class Settings:
    vault: Path
    sources: tuple[Path, ...]
    state_path: Path
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL
    mode: str = DEFAULT_MODE
    reasoning_effort: str = "medium"
    timeout: float = 120.0
    auto_commit: bool = True
    retry_ai: bool = False
    dry_run: bool = False
    api_key: str | None = field(default=None, repr=False)
    api_key_file: Path | None = None
    apple_notes_database: Path | None = None
    include_deleted_notes: bool = False
    config_path: Path | None = None
    auto_transcribe: bool = True
    stt_command: str = DEFAULT_STT_COMMAND
    stt_ffmpeg_command: str = DEFAULT_STT_FFMPEG_COMMAND
    stt_model: Path | None = None
    stt_language: str = DEFAULT_STT_LANGUAGE
    stt_timeout: float = DEFAULT_STT_TIMEOUT

    @property
    def proxy_url(self) -> str:
        """Compatibility spelling for the old prototype's endpoint option."""

        return self.endpoint

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ConfigError(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")
        if not self.endpoint.strip():
            raise ConfigError("endpoint must not be empty")
        if self.timeout <= 0:
            raise ConfigError("timeout must be greater than zero")
        if not self.stt_command.strip():
            raise ConfigError("stt_command must not be empty")
        if not self.stt_ffmpeg_command.strip():
            raise ConfigError("stt_ffmpeg_command must not be empty")
        if not self.stt_language.strip():
            raise ConfigError("stt_language must not be empty")
        if self.stt_timeout <= 0:
            raise ConfigError("stt_timeout must be greater than zero")


def _default_sources() -> tuple[Path, ...]:
    home = Path.home()
    return (
        home / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings",
        home / "Library/Mobile Documents/com~apple~CloudDocs/AhaMomentInbox",
    )


def _default_apple_notes_database() -> Path | None:
    candidate = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    return candidate if candidate.is_file() else None


def _as_mapping(cli: Mapping[str, Any] | Any | None) -> dict[str, Any]:
    if cli is None:
        return {}
    if isinstance(cli, Mapping):
        return dict(cli)
    values = vars(cli)
    return {key: value for key, value in values.items() if value is not None}


def _env_value(env: Mapping[str, str], name: str) -> str | None:
    for key in (f"AHA_{name}", f"AHA_MOMENT_RECORDER_{name}"):
        if key in env and env[key] != "":
            return env[key]
    return None


def _read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise ConfigError("TOML configuration requires Python 3.11 or newer")
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML config: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError("config must contain a TOML table")
    return value


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        if "api_key" in value or "token" in value or "secret" in value:
            return True
        return any(_contains_secret_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_secret_key(item) for item in value)
    return False


def _flatten_config(value: Mapping[str, Any]) -> dict[str, Any]:
    if _contains_secret_key(value):
        raise ConfigError("secrets may only be supplied through environment or key-file")
    result = dict(value)
    for section_name in ("aha_moment_recorder", "record_bridge", "bridge", "record"):
        section = value.get(section_name)
        if isinstance(section, Mapping):
            result.update(section)
    return result


def _path(value: Any, *, base: Path) -> Path:
    if value is None or str(value).strip() == "":
        raise ConfigError("path value must not be empty")
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _paths(value: Any, *, base: Path) -> tuple[Path, ...]:
    if isinstance(value, str):
        items = [item for item in value.split(os.pathsep) if item]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise ConfigError("sources must be a TOML array or path-separated string")
    if not items:
        raise ConfigError("at least one source root is required")
    return tuple(_path(item, base=base) for item in items)


def _bool(value: Any, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean")


def _choose(
    name: str,
    *,
    config: Mapping[str, Any],
    env: Mapping[str, str],
    cli: Mapping[str, Any],
    aliases: tuple[str, ...] = (),
    env_names: tuple[str, ...] = (),
    default: Any = None,
) -> Any:
    keys = (name, *aliases)
    for key in keys:
        if key in cli and cli[key] is not None:
            return cli[key]
    for env_name in (name, *env_names, *aliases):
        value = _env_value(env, env_name.upper().replace("-", "_"))
        if value is not None:
            return value
    for key in keys:
        if key in config and config[key] is not None:
            return config[key]
    return default


def load_settings(
    config_path: Path | str | None = None,
    *,
    env: Mapping[str, str] | None = None,
    cli: Mapping[str, Any] | Any | None = None,
    cwd: Path | None = None,
) -> Settings:
    """Load settings in the documented TOML < env < CLI order.

    Relative paths from TOML are relative to the TOML file.  Relative paths
    from environment variables or CLI options are relative to ``cwd``.
    """

    environment = dict(os.environ if env is None else env)
    command_line = _as_mapping(cli)
    working_dir = (cwd or Path.cwd()).expanduser().resolve()
    requested_config = config_path
    if requested_config is None:
        requested_config = command_line.get("config") or _env_value(environment, "CONFIG")
    config_file = _path(requested_config, base=working_dir) if requested_config else None
    config_values: dict[str, Any] = {}
    config_base = working_dir
    if config_file is not None:
        if not config_file.is_file():
            raise ConfigError(f"config file does not exist: {config_file}")
        config_values = _flatten_config(_read_toml(config_file))
        config_base = config_file.parent

    def choose(name: str, *, aliases: tuple[str, ...] = (), env_names: tuple[str, ...] = (), default: Any = None) -> Any:
        return _choose(
            name,
            config=config_values,
            env=environment,
            cli=command_line,
            aliases=aliases,
            env_names=env_names,
            default=default,
        )

    def value_base(
        name: str,
        *,
        aliases: tuple[str, ...] = (),
        env_names: tuple[str, ...] = (),
    ) -> Path:
        if any(command_line.get(key) is not None for key in (name, *aliases)):
            return working_dir
        if any(
            _env_value(environment, env_name.upper().replace("-", "_")) is not None
            for env_name in (name, *env_names, *aliases)
        ):
            return working_dir
        return config_base

    vault = _path(
        choose("vault", default=Path.home() / "Documents/Aha Moment Vault"),
        base=value_base("vault"),
    )
    source_value = choose("sources", aliases=("source",), default=_default_sources())
    sources = _paths(source_value, base=value_base("sources", aliases=("source",)))
    state_value = choose("state_path", aliases=("state",), default=None)
    state_path = (
        _path(
            state_value,
            base=value_base("state_path", aliases=("state",)),
        )
        if state_value
        else vault / ".bridge/state.json"
    )
    endpoint = str(choose("endpoint", aliases=("proxy_url",), env_names=("PROXY_URL",), default=DEFAULT_ENDPOINT)).rstrip("/")
    model = str(choose("model", default=DEFAULT_MODEL))
    mode = str(choose("mode", default=DEFAULT_MODE))
    reasoning_effort = str(choose("reasoning_effort", aliases=("reasoning",), default="medium"))
    timeout_value = choose("timeout", default=120.0)
    try:
        timeout = float(timeout_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError("timeout must be a number") from exc

    no_git_commit = command_line.get("no_git_commit")
    if no_git_commit is True:
        auto_commit = False
    else:
        auto_commit = _bool(choose("auto_commit", default=True), name="auto_commit")
    retry_ai = _bool(choose("retry_ai", default=False), name="retry_ai")
    dry_run = _bool(choose("dry_run", default=False), name="dry_run")
    auto_transcribe = (
        False
        if command_line.get("no_transcribe") is True
        else _bool(choose("auto_transcribe", default=True), name="auto_transcribe")
    )
    stt_command = str(
        choose("stt_command", env_names=("STT_COMMAND",), default=DEFAULT_STT_COMMAND)
    )
    stt_ffmpeg_command = str(
        choose(
            "stt_ffmpeg_command",
            env_names=("STT_FFMPEG_COMMAND",),
            default=DEFAULT_STT_FFMPEG_COMMAND,
        )
    )
    stt_model_value = choose(
        "stt_model",
        env_names=("STT_MODEL", "TRANSCRIBER_MODEL"),
        default=None,
    )
    stt_model = (
        _path(stt_model_value, base=value_base("stt_model"))
        if stt_model_value
        else None
    )
    stt_language = str(
        choose("stt_language", env_names=("STT_LANGUAGE",), default=DEFAULT_STT_LANGUAGE)
    )
    stt_timeout_value = choose(
        "stt_timeout", env_names=("STT_TIMEOUT",), default=DEFAULT_STT_TIMEOUT
    )
    try:
        stt_timeout = float(stt_timeout_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError("stt_timeout must be a number") from exc

    api_key_file_value = choose("api_key_file", default=None)
    api_key_file = (
        _path(api_key_file_value, base=value_base("api_key_file"))
        if api_key_file_value
        else None
    )
    cli_key_file = command_line.get("api_key_file")
    api_key = None
    if cli_key_file is not None and api_key_file is not None:
        try:
            api_key = api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigError(f"cannot read API key file: {api_key_file}") from exc
        if not api_key:
            raise ConfigError(f"API key file is empty: {api_key_file}")
    elif _env_value(environment, "API_KEY") is not None:
        api_key = _env_value(environment, "API_KEY")
    elif api_key_file is not None:
        try:
            api_key = api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigError(f"cannot read API key file: {api_key_file}") from exc
        if not api_key:
            raise ConfigError(f"API key file is empty: {api_key_file}")

    apple_notes_value = (
        None
        if command_line.get("no_apple_notes") is True
        else choose("apple_notes_database", default=_default_apple_notes_database())
    )
    apple_notes_database = (
        _path(apple_notes_value, base=value_base("apple_notes_database"))
        if apple_notes_value
        else None
    )
    include_deleted_notes = _bool(
        choose("include_deleted_notes", aliases=("include_deleted",), default=False),
        name="include_deleted_notes",
    )

    return Settings(
        vault=vault,
        sources=sources,
        state_path=state_path,
        endpoint=endpoint,
        model=model,
        mode=mode,
        reasoning_effort=reasoning_effort,
        timeout=timeout,
        auto_commit=auto_commit,
        retry_ai=retry_ai,
        dry_run=dry_run,
        api_key=api_key,
        api_key_file=api_key_file,
        apple_notes_database=apple_notes_database,
        include_deleted_notes=include_deleted_notes,
        config_path=config_file,
        auto_transcribe=auto_transcribe,
        stt_command=stt_command,
        stt_ffmpeg_command=stt_ffmpeg_command,
        stt_model=stt_model,
        stt_language=stt_language,
        stt_timeout=stt_timeout,
    )


def write_config(path: Path | str, settings: Settings, *, overwrite: bool = False) -> Path:
    """Write a secret-free TOML configuration for an initialized workspace."""

    target = Path(path).expanduser().resolve()
    if target.exists() and not overwrite:
        raise ConfigError(f"config file already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    def quote(value: object) -> str:
        return json.dumps(str(value), ensure_ascii=False)

    lines = [
        "# Aha Moment Recorder configuration. Do not put API keys in this file.",
        "[aha_moment_recorder]",
        f"vault = {quote(settings.vault)}",
        "sources = [",
        *[f"  {quote(source)}," for source in settings.sources],
        "]",
        f"state = {quote(settings.state_path)}",
        f"endpoint = {quote(settings.endpoint)}",
        f"model = {quote(settings.model)}",
        f"mode = {quote(settings.mode)}",
        f"reasoning_effort = {quote(settings.reasoning_effort)}",
        f"timeout = {settings.timeout:g}",
        f"auto_commit = {str(settings.auto_commit).lower()}",
        f"retry_ai = {str(settings.retry_ai).lower()}",
        f"dry_run = {str(settings.dry_run).lower()}",
        f"auto_transcribe = {str(settings.auto_transcribe).lower()}",
        f"stt_command = {quote(settings.stt_command)}",
        f"stt_ffmpeg_command = {quote(settings.stt_ffmpeg_command)}",
        f"stt_language = {quote(settings.stt_language)}",
        f"stt_timeout = {settings.stt_timeout:g}",
    ]
    if settings.stt_model is not None:
        lines.append(f"stt_model = {quote(settings.stt_model)}")
    if settings.api_key_file is not None:
        lines.append(f"api_key_file = {quote(settings.api_key_file)}")
    if settings.apple_notes_database is not None:
        lines.append(f"apple_notes_database = {quote(settings.apple_notes_database)}")
    lines.append(f"include_deleted_notes = {str(settings.include_deleted_notes).lower()}")
    lines.extend(
        [
            "",
            "# Authentication is read from AHA_API_KEY or api_key_file.",
            "",
        ]
    )
    target.write_text("\n".join(lines), encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return target


def environment_without_secrets() -> dict[str, str]:
    """Return config diagnostics without exposing secret values."""

    return {
        key: ("<set>" if "KEY" in key or "TOKEN" in key or "SECRET" in key else value)
        for key, value in os.environ.items()
        if key.startswith("AHA_") or key.startswith("AHA_MOMENT_RECORDER_")
    }
