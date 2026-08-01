"""Strict four-field AI organization contract and HTTP adapter."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


FOUR_FIELDS = frozenset({"classification", "topic", "structured_output", "summary"})


class OrganizationError(ValueError):
    """Raised when an AI response does not satisfy the four-field contract."""


def _non_empty_text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise OrganizationError(f"{field} must be a non-empty string")
    return value.strip()


def _topic(value: Any) -> str | tuple[str, ...]:
    if type(value) is str:
        normalized = value.strip()
        if not normalized:
            raise OrganizationError("topic must not be empty")
        return normalized
    if isinstance(value, (list, tuple)):
        if any(type(item) is not str or not item.strip() for item in value):
            raise OrganizationError("topic must be a string or list of strings")
        return tuple(item.strip() for item in value)
    raise OrganizationError("topic must be a string or list of strings")


def _json_value(value: Any, field: str) -> Any:
    if value is None or not isinstance(value, (str, list, dict)):
        raise OrganizationError(f"{field} must be a string, list, or object")
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise OrganizationError(f"{field} must be JSON serializable") from exc
    return value


@dataclass(frozen=True)
class Organization:
    classification: str
    topic: str | tuple[str, ...]
    structured_output: str | list[Any] | dict[str, Any]
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "classification", _non_empty_text(self.classification, "classification"))
        object.__setattr__(self, "topic", _topic(self.topic))
        object.__setattr__(self, "structured_output", _json_value(self.structured_output, "structured_output"))
        object.__setattr__(self, "summary", _non_empty_text(self.summary, "summary"))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Organization":
        keys = set(value)
        missing = sorted(FOUR_FIELDS - keys)
        extra = sorted(keys - FOUR_FIELDS)
        if missing:
            raise OrganizationError(f"AI response missing: {', '.join(missing)}")
        if extra:
            raise OrganizationError(f"AI response has unexpected fields: {', '.join(extra)}")
        return cls(
            classification=value["classification"],
            topic=value["topic"],
            structured_output=value["structured_output"],
            summary=value["summary"],
        )

    def as_dict(self) -> dict[str, Any]:
        topic: str | list[str]
        if isinstance(self.topic, tuple):
            topic = list(self.topic)
        else:
            topic = self.topic
        return {
            "classification": self.classification,
            "topic": topic,
            "structured_output": self.structured_output,
            "summary": self.summary,
        }


def _decode_json_object(content: str) -> Mapping[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    candidates = [match.start() for match in re.finditer(r"\{", text)] or [0]
    for start in candidates:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            return value
    raise OrganizationError("AI response is not a JSON object")


def parse_organization(content: str | Mapping[str, Any] | Organization) -> Organization:
    if isinstance(content, Organization):
        return content
    if isinstance(content, Mapping):
        return Organization.from_mapping(content)
    if type(content) is not str:
        raise OrganizationError("AI response must be text or an object")
    return Organization.from_mapping(_decode_json_object(content))


def build_prompt(text: str) -> str:
    return (
        "請把下面一筆個人記錄做通用整理，只輸出 JSON，不要 Markdown code fence。"
        "欄位必須恰好是 classification、topic、structured_output、summary。"
        "classification 是單一主要分類；topic 可是字串或字串陣列；"
        "structured_output 是忠於原意的可讀整理；summary 是簡短摘要。"
        "不要額外產生待辦欄位；若內容本身是待辦，可把待辦當作 classification。"
        "不要捏造來源沒有的資訊。\n\n記錄內容：\n"
        + text
    )


class HttpTransport(Protocol):
    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> Mapping[str, Any] | str: ...


class UrllibTransport:
    """OpenAI-compatible HTTP transport implemented with Python stdlib."""

    def post(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> Mapping[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers=dict(headers),
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            value = json.loads(body)
        except urllib.error.HTTPError as exc:
            raise OrganizationError(f"AI HTTP request failed with status {exc.code}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise OrganizationError(f"AI HTTP request failed: {type(exc).__name__}") from exc
        if not isinstance(value, Mapping):
            raise OrganizationError("AI HTTP response must be a JSON object")
        return value


class OpenAICompatibleOrganizer:
    """Call any provider exposing the OpenAI-compatible chat completions route."""

    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        api_key: str | None = None,
        api_key_provider: Callable[[], str | None] | None = None,
        reasoning_effort: str = "medium",
        timeout: float = 120.0,
        transport: HttpTransport | None = None,
        http_client: HttpTransport | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_provider = api_key_provider
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout
        self.transport = transport or http_client or UrllibTransport()

    @property
    def completions_url(self) -> str:
        return (
            self.endpoint
            if self.endpoint.endswith("/chat/completions")
            else f"{self.endpoint}/chat/completions"
        )

    def organize(self, text: str) -> Organization:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是個人記錄整理助手。"},
                {"role": "user", "content": build_prompt(text)},
            ],
            "reasoning_effort": self.reasoning_effort,
            "temperature": 0,
        }
        key = self.api_key_provider() if self.api_key_provider else self.api_key
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if hasattr(self.transport, "post"):
            response = self.transport.post(self.completions_url, payload, headers, self.timeout)
        elif hasattr(self.transport, "post_json"):
            response = self.transport.post_json(self.completions_url, payload, headers, self.timeout)  # type: ignore[attr-defined]
        else:
            raise OrganizationError("HTTP transport must provide post or post_json")
        if isinstance(response, bytes):
            try:
                response_value = json.loads(response.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise OrganizationError("AI HTTP response is not valid JSON") from exc
        elif isinstance(response, str):
            try:
                response_value: Mapping[str, Any] = json.loads(response)
            except json.JSONDecodeError as exc:
                raise OrganizationError("AI HTTP response is not valid JSON") from exc
        else:
            response_value = response
        try:
            content = response_value["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OrganizationError("AI response has no chat content") from exc
        return parse_organization(content)
