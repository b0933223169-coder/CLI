"""Structured, redacted Playwright network events for the GUI log panel."""
from __future__ import annotations

import json
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LOG_MARKER = "@@COOL_PLAYWRIGHT_LOG@@"
MAX_LOG_BODY = 16_384
SENSITIVE_NAME = re.compile(
    r"(pass(word)?|token|secret|cookie|authorization|auth|session|csrf|api[_-]?key|credential|oauth|code|state|signature)",
    re.IGNORECASE,
)
SENSITIVE_BODY_KEY = (
    r"(?:pass(?:word)?|token|secret|cookie|authorization|session|csrf|api[_-]?key|oauth|code|state|signature)"
)


def _emit(event: str, **details) -> None:
    record = {"event": event, **details}
    print(
        LOG_MARKER + json.dumps(record, ensure_ascii=False, separators=(",", ":")),
        file=sys.stdout,
        flush=True,
    )


def _safe_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        query = [
            (key, "[REDACTED]" if SENSITIVE_NAME.search(key) else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    except ValueError:
        return url


def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
    safe = {}
    for name, value in headers.items():
        if SENSITIVE_NAME.search(name):
            safe[name] = "[REDACTED]"
        elif name.lower() in ("location", "referer", "referrer"):
            safe[name] = _safe_url(value)
        else:
            safe[name] = value
    return safe


def _is_auth_endpoint(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    path = parts.path.lower()
    return (
        host == "accounts.google.com"
        or host.endswith(".accounts.google.com")
        or host == "oauth2.googleapis.com"
        or any(marker in path for marker in ("/login", "/signin", "/sign-in", "/oauth", "/auth"))
    )


def _safe_json(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SENSITIVE_NAME.search(str(key)) else _safe_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_json(item) for item in value]
    return value


def _safe_body(body: str | None, content_type: str) -> str | None:
    if not body:
        return body
    content_type = content_type.lower()
    if "multipart/form-data" in content_type:
        return "[omitted: multipart payload]"

    safe_body = body
    if "json" in content_type:
        try:
            safe_body = json.dumps(
                _safe_json(json.loads(body)),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except (json.JSONDecodeError, TypeError):
            safe_body = re.sub(
                rf'(["\']?[\w.-]*{SENSITIVE_BODY_KEY}[\w.-]*["\']?\s*[:=]\s*)["\']?[^,}}"\'&\s]*',
                r'\1"[REDACTED]"',
                safe_body,
                flags=re.IGNORECASE,
            )
    elif "application/x-www-form-urlencoded" in content_type:
        from urllib.parse import parse_qsl

        safe_body = urlencode([
            (key, "[REDACTED]" if SENSITIVE_NAME.search(key) else value)
            for key, value in parse_qsl(body, keep_blank_values=True)
        ])
    elif not any(kind in content_type for kind in ("text/", "xml", "javascript")):
        return "[omitted: non-text payload]"
    else:
        def redact_input(match):
            tag = match.group(0)
            if not SENSITIVE_NAME.search(tag):
                return tag
            return re.sub(
                r'(\bvalue\s*=\s*)(?:"[^"]*"|\'[^\']*\'|[^\s>]+)',
                r'\1"[REDACTED]"',
                tag,
                count=1,
                flags=re.IGNORECASE,
            )

        safe_body = re.sub(
            r"<input\b[^>]*>",
            redact_input,
            safe_body,
            flags=re.IGNORECASE,
        )
        safe_body = re.sub(
            rf'({SENSITIVE_BODY_KEY}\s*[:=]\s*)["\']?[^,}}"\'&\s<]*',
            r'\1[REDACTED]',
            safe_body,
            flags=re.IGNORECASE,
        )

    if len(safe_body) > MAX_LOG_BODY:
        return safe_body[:MAX_LOG_BODY] + f"\n[truncated at {MAX_LOG_BODY} characters]"
    return safe_body


def attach_context_logging(context) -> None:
    """Capture network request/response metadata and safe text payloads."""
    def on_request(request):
        is_auth_endpoint = _is_auth_endpoint(request.url)
        try:
            headers = request.all_headers()
        except Exception:
            headers = request.headers
        try:
            post_data = request.post_data
            content_type = headers.get("content-type", "")
            safe_data = (
                "[omitted: authentication endpoint]"
                if post_data and is_auth_endpoint
                else _safe_body(post_data, content_type)
            )
            if safe_data and len(safe_data) > MAX_LOG_BODY:
                safe_data = safe_data[:MAX_LOG_BODY] + f"\n[truncated at {MAX_LOG_BODY} characters]"
        except Exception:
            safe_data = "[unavailable]"
        _emit(
            "request",
            method=request.method,
            url=_safe_url(request.url),
            resource_type=request.resource_type,
            headers=_safe_headers(headers),
            body=safe_data,
        )

    def on_response(response):
        is_auth_endpoint = _is_auth_endpoint(response.url)
        try:
            headers = response.all_headers()
        except Exception:
            headers = response.headers
        content_type = headers.get("content-type", "")
        body = None
        body_error = None
        length = headers.get("content-length")
        try:
            should_read_body = (
                any(kind in content_type.lower() for kind in ("text/", "json", "xml", "javascript"))
                and (length is None or int(length) <= 1_048_576)
                and not is_auth_endpoint
            )
            if should_read_body:
                body = _safe_body(response.body().decode("utf-8", errors="replace"), content_type)
        except Exception as exc:
            body = "[unavailable]"
            body_error = str(exc)
        _emit(
            "response",
            status=response.status,
            status_text=response.status_text,
            url=_safe_url(response.url),
            headers=_safe_headers(headers),
            body=body,
            body_error=body_error,
        )

    def on_request_failed(request):
        _emit(
            "requestfailed",
            method=request.method,
            url=_safe_url(request.url),
            failure=request.failure,
        )

    context.on("request", on_request)
    context.on("response", on_response)
    context.on("requestfailed", on_request_failed)
