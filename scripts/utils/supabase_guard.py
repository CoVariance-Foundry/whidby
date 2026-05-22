"""Supabase guard helpers shared by operational scripts."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

try:
    from postgrest.exceptions import APIError as PostgrestAPIError
except ImportError:  # pragma: no cover - dependency may be absent in lightweight envs.
    POSTGREST_API_ERROR_TYPES: tuple[type[BaseException], ...] = ()
else:
    POSTGREST_API_ERROR_TYPES = (PostgrestAPIError,)

MISSING_COLUMN_ERROR_CODES = {"42703", "PGRST204"}


def supabase_project_ref(supabase_url: str) -> str | None:
    """Extract the Supabase project ref from a project URL."""
    parsed = urlparse(supabase_url.strip())
    if parsed.scheme != "https" or parsed.hostname is None:
        return None
    suffix = ".supabase.co"
    if not parsed.hostname.endswith(suffix):
        return None
    project_ref = parsed.hostname[: -len(suffix)]
    if not project_ref or "." in project_ref:
        return None
    return project_ref


def _error_code(exc: BaseException) -> str | None:
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        return code
    for arg in getattr(exc, "args", ()):
        if isinstance(arg, dict) and isinstance(arg.get("code"), str):
            return arg["code"]
    return None


def _error_text(exc: BaseException) -> str:
    parts: list[str] = []
    for attribute in ("message", "details", "hint"):
        value: Any = getattr(exc, attribute, None)
        if value:
            parts.append(str(value))
    parts.extend(str(arg) for arg in getattr(exc, "args", ()) if arg)
    return " ".join(parts).lower()


def is_postgrest_missing_column_error(exc: BaseException) -> bool:
    """Return true for PostgREST errors caused by missing selected columns."""
    if _error_code(exc) in MISSING_COLUMN_ERROR_CODES:
        return True

    text = _error_text(exc)
    return "column" in text and any(
        marker in text
        for marker in (
            "does not exist",
            "could not find",
            "not found",
            "schema cache",
            "undefined column",
        )
    )
