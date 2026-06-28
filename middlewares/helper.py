import json
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

REDACT_HEADERS: set[str] = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
}

REDACT_BODY_FIELDS: set[str] = {
    "password",
    "hashed_password",
    "secret",
    "secret_key",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
}


def redact_value(value: Any) -> Any:
    """Recursively redact sensitive fields inside dicts and lists."""
    if isinstance(value, Mapping):
        redacted_map: dict[Any, Any] = {}
        for key in value.keys():
            inner = value[key]
            if key.lower() in REDACT_BODY_FIELDS:
                redacted_map[key] = REDACTED
            else:
                redacted_map[key] = redact_value(inner)
        return redacted_map
    if isinstance(value, list):
        redacted_list: list[Any] = []
        for item in value:
            redacted_list.append(redact_value(item))
        return redacted_list
    return value


def truncate_for_display(
    value: Any,
    *,
    max_list_items: int,
    max_string_length: int,
) -> Any:
    """Recursively shorten long strings/lists for log readability.

    * Strings longer than ``max_string_length`` are cut to that length and
      suffixed with ``"... (N chars)"`` so the original size is still visible.
    * Lists longer than ``max_list_items`` keep the first N elements and
      append a ``"... +M more items"`` placeholder.
    * Dicts pass through (their keys are domain-specific — truncating them
      would make the log misleading).

    Run AFTER redaction so we don't accidentally truncate something that
    would have been redacted into ``"[REDACTED]"`` anyway.
    """
    if isinstance(value, str):
        if max_string_length > 0 and len(value) > max_string_length:
            head = value[:max_string_length]
            return head + f"... ({len(value)} chars)"
        return value
    if isinstance(value, Mapping):
        truncated_map: dict[Any, Any] = {}
        for key in value.keys():
            inner = value[key]
            truncated_map[key] = truncate_for_display(
                inner,
                max_list_items=max_list_items,
                max_string_length=max_string_length,
            )
        return truncated_map
    if isinstance(value, list):
        if max_list_items > 0 and len(value) > max_list_items:
            head_list: list[Any] = []
            head_slice = value[:max_list_items]
            for item in head_slice:
                head_list.append(
                    truncate_for_display(
                        item,
                        max_list_items=max_list_items,
                        max_string_length=max_string_length,
                    )
                )
            remaining = len(value) - max_list_items
            head_list.append(f"... +{remaining} more items")
            return head_list

        truncated_list: list[Any] = []
        for item in value:
            truncated_list.append(
                truncate_for_display(
                    item,
                    max_list_items=max_list_items,
                    max_string_length=max_string_length,
                )
            )
        return truncated_list
    return value


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values replaced by REDACTED."""
    result: dict[str, str] = {}
    for name in headers.keys():
        value = headers[name]
        if name.lower() in REDACT_HEADERS:
            result[name] = REDACTED
        else:
            result[name] = value
    return result


def is_json(content_type: str | None) -> bool:
    """Return True for application/json and +json media types."""
    if not content_type:
        return False
    main = content_type.split(";", 1)[0].strip().lower()
    return main == "application/json" or main.endswith("+json")


def decode_json_body(body: bytes) -> Any | str:
    """Return parsed JSON, or a placeholder if the bytes don't decode."""
    if not body:
        return None
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return f"[non-json body: {len(body)} bytes]"
