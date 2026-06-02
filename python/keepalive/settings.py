"""Pure settings resolution: merge CLI options with a named profile.

Explicit CLI flags always win over profile presets, matching the PowerShell
``$PSBoundParameters.ContainsKey`` behaviour. Kept side-effect free so the
precedence rules are unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_MINUTES = 0

# Profile keys are the PascalCase names used in keepalive.json (shared with the
# PowerShell version) mapped to our snake_case settings fields.
_PROFILE_KEY_MAP = {
    "IntervalSeconds": "interval_seconds",
    "Minutes": "minutes",
    "Quiet": "quiet",
    "SystemOnly": "system_only",
    "AllMicrosoftApps": "all_microsoft_apps",
    "BrowserKeepAlive": "browser_keep_alive",
    "Tray": "tray",
}


@dataclass(frozen=True)
class Settings:
    """Resolved run settings after merging CLI flags and a profile preset."""

    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    minutes: int = DEFAULT_MINUTES
    quiet: bool = False
    system_only: bool = False
    all_microsoft_apps: bool = False
    browser_keep_alive: bool = False
    tray: bool = False


def resolve_settings(
    cli: Dict[str, Any], preset: Optional[Dict[str, Any]] = None
) -> Settings:
    """Merge a CLI option dict with a profile preset into final ``Settings``.

    ``cli`` values of ``None`` mean "not explicitly provided" and fall back to
    the preset (if any), then to the hard default. Boolean flags that are
    ``False`` also defer to a preset that turns them on — presets can enable an
    option but an explicit CLI flag always takes precedence.
    """
    preset = preset or {}
    # Translate the PascalCase profile keys to our field names.
    pre: Dict[str, Any] = {}
    for raw_key, value in preset.items():
        field = _PROFILE_KEY_MAP.get(raw_key)
        if field is not None:
            pre[field] = value

    def pick(field: str, default: Any) -> Any:
        cli_value = cli.get(field)
        if cli_value is not None and cli_value is not False:
            return cli_value
        if field in pre:
            return pre[field]
        return cli_value if cli_value is not None else default

    return Settings(
        interval_seconds=int(pick("interval_seconds", DEFAULT_INTERVAL_SECONDS)),
        minutes=int(pick("minutes", DEFAULT_MINUTES)),
        quiet=bool(pick("quiet", False)),
        system_only=bool(pick("system_only", False)),
        all_microsoft_apps=bool(pick("all_microsoft_apps", False)),
        browser_keep_alive=bool(pick("browser_keep_alive", False)),
        tray=bool(pick("tray", False)),
    )
