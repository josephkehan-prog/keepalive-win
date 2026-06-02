"""M365 browser-tab keep-alive (CDP) URL helpers.

Pure URL classification used by the ``--browser-keep-alive`` feature. The
actual WebSocket/CDP traffic lives in :mod:`keepalive.nudge`.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Mapping, Sequence

# Substring patterns that identify an M365 web property. Matched
# case-insensitively against tab URLs.
M365_URL_PATTERNS = (
    r"outlook\.office",
    r"teams\.microsoft",
    r"\.sharepoint\.com",
    r"\.office\.com",
    r"onedrive\.live\.com",
    r"\.microsoftonline\.com",
)

_COMPILED = tuple(re.compile(p, re.IGNORECASE) for p in M365_URL_PATTERNS)


def m365_url_patterns() -> List[str]:
    """Return the raw regex patterns used to identify M365 URLs."""
    return list(M365_URL_PATTERNS)


def is_m365_url(url: str) -> bool:
    """True when ``url`` points at a known M365 web property."""
    if not url or not url.strip():
        return False
    return any(pattern.search(url) for pattern in _COMPILED)


def select_m365_tabs(tabs: Sequence[Mapping[str, object]] | None) -> List[Mapping[str, object]]:
    """Return only the tabs whose ``url`` matches an M365 pattern.

    ``tabs`` is the list of dicts returned by the Chrome/Edge ``/json``
    DevTools endpoint. A ``None`` input yields an empty list.
    """
    if not tabs:
        return []
    selected: List[Mapping[str, object]] = []
    for tab in tabs:
        url = str(tab.get("url", "")) if isinstance(tab, Mapping) else ""
        if is_m365_url(url):
            selected.append(tab)
    return selected
