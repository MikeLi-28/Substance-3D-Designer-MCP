"""Construct JSON-safe references without leaking API object representations."""

from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def strip_temporary_dependency(url: str) -> str:
    """Remove only the unstable dependency query parameter from a resource URL."""

    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "dependency"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def make_library_resource_ref(
    package_url: str,
    resource_identifier: str,
    runtime_url: str,
    label: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Return stable identity plus the current session's resolvable URL."""

    stable_runtime_url = strip_temporary_dependency(runtime_url)
    return {
        "package_url": package_url,
        "resource_identifier": resource_identifier,
        "stable_key": f"{package_url}::{stable_runtime_url}",
        "runtime_url": runtime_url,
        "label": label,
        "category": category,
    }
