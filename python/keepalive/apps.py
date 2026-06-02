"""Microsoft desktop-app matching for the ``--all-microsoft-apps`` feature.

Pure helpers — the actual per-window ``PostMessage`` nudge lives in
:mod:`keepalive.nudge`.
"""

from __future__ import annotations

from typing import List

# Microsoft desktop apps that --all-microsoft-apps nudges per-window so they
# stay non-idle even when backgrounded. Process names are lowercase, without
# the ".exe" suffix.
MICROSOFT_APP_PROCESS_NAMES = (
    "outlook",   # Outlook
    "teams",     # Teams (classic client)
    "ms-teams",  # Teams (new client)
    "onenote",   # OneNote
    "winword",   # Word
    "excel",     # Excel
    "powerpnt",  # PowerPoint
    "msaccess",  # Access
    "mspub",     # Publisher
    "visio",     # Visio
    "winproj",   # Project
    "lync",      # Skype for Business
    "onedrive",  # OneDrive
    "msedge",    # Edge (M365 web apps)
)


def microsoft_app_process_names() -> List[str]:
    """Return the list of targeted Microsoft app process names."""
    return list(MICROSOFT_APP_PROCESS_NAMES)


def is_microsoft_app(process_name: str) -> bool:
    """True when a process name is a targeted Microsoft app.

    Case-insensitive and tolerant of an optional ".exe" suffix so it matches
    both friendly process names and raw image names. Uses a plain ASCII
    lower-casing (``str.lower``) — locale-independent for the ASCII image
    names we care about (e.g. VISIO / LYNC).
    """
    if process_name is None or not process_name.strip():
        return False
    name = process_name.strip().lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name in MICROSOFT_APP_PROCESS_NAMES
