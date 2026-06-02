"""Named-profile loading from ``keepalive.json``.

Mirrors the ``Read-ProfileConfig`` / ``Get-ProfileSettings`` helpers from the
PowerShell original. Profiles let users save presets like ``meeting`` or
``focus`` and load them with ``--profile NAME``; explicit CLI flags always win.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, Optional

# PID file name used to track a detached --headless process.
PID_FILE_NAME = "keepalive.pid"

# Stable name of the Windows scheduled task registered by --install.
STARTUP_TASK_NAME = "KeepAlive"


def startup_task_name() -> str:
    """Return the stable task name used by --install / --uninstall."""
    return STARTUP_TASK_NAME


def pid_file_path() -> str:
    """Return the path of the headless-process PID file (under TEMP)."""
    return os.path.join(tempfile.gettempdir(), PID_FILE_NAME)


def read_profile_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Load the ``profiles`` object from a config file.

    Returns ``None`` when the file is missing or the JSON is malformed, so a
    broken config never crashes startup — the caller falls back to defaults.
    """
    if not config_path or not os.path.isfile(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    profiles = data.get("profiles")
    return profiles if isinstance(profiles, dict) else None


def profile_settings(profiles: Optional[Dict[str, Any]], profile_name: str) -> Optional[Dict[str, Any]]:
    """Return the settings dict for a named profile, or ``None``.

    ``None`` is returned for a missing profiles object, an empty name, or an
    unknown profile name.
    """
    if not profiles or not profile_name or not profile_name.strip():
        return None
    preset = profiles.get(profile_name)
    return preset if isinstance(preset, dict) else None
