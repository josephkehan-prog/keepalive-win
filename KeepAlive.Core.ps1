# KeepAlive.Core.ps1 — pure, testable logic for the keepalive CLI.
# No side effects here; the Win32 calls live in keepalive.ps1.

# Minimum interval guard: anything faster than this is pointless thrash.
$script:MinIntervalSeconds = 10

function Test-IntervalValid {
    param([int]$IntervalSeconds)
    return ($IntervalSeconds -ge $script:MinIntervalSeconds)
}

function Get-EndTime {
    param([datetime]$Start, [int]$Minutes)
    if ($Minutes -le 0) { return $null }   # 0 or negative = run until stopped
    return $Start.AddMinutes($Minutes)
}

function Get-AwakeFlags {
    # Composes the SetThreadExecutionState bitmask that keeps Windows awake.
    # ES_CONTINUOUS (0x80000000) is always set so the state persists across the run.
    # ES_SYSTEM_REQUIRED (0x1) blocks system sleep; ES_DISPLAY_REQUIRED (0x2) blocks
    # display-off. Default keeps both; clearing KeepDisplayOn lets the monitor sleep
    # while the machine itself stays awake (avoids sleep/idle logout, saves the screen).
    param(
        [bool]$KeepSystemAwake = $true,
        [bool]$KeepDisplayOn   = $true
    )
    $ES_CONTINUOUS       = [uint32]2147483648
    $ES_SYSTEM_REQUIRED  = [uint32]1
    $ES_DISPLAY_REQUIRED = [uint32]2
    $flags = $ES_CONTINUOUS
    if ($KeepSystemAwake) { $flags = $flags -bor $ES_SYSTEM_REQUIRED }
    if ($KeepDisplayOn)   { $flags = $flags -bor $ES_DISPLAY_REQUIRED }
    return [uint32]$flags
}

function Test-ShouldStop {
    param([datetime]$Now, $EndTime)
    if ($null -eq $EndTime) { return $false }   # no end time = never auto-stop
    return ($Now -ge [datetime]$EndTime)
}

# Name of the scheduled task registered by -Install (run-at-logon feature).
$script:StartupTaskName = 'KeepAlive'

function Get-StartupTaskName {
    return $script:StartupTaskName
}

# Builds the pwsh argument string used to relaunch this CLI — for the run-at-logon
# task (-Install) and for the detached -Headless launch. Pure string assembly so it
# can be unit-tested without touching Task Scheduler or spawning a process.
# Only non-default flags are emitted, so a plain relaunch stays minimal.
function Get-StartupArguments {
    param(
        [string]$ScriptPath,
        [int]$IntervalSeconds = 60,
        [int]$Minutes = 0,
        [switch]$Quiet,
        [switch]$SystemOnly,
        [switch]$AllMicrosoftApps,
        [switch]$Hidden
    )
    $parts = @('-NoProfile', '-ExecutionPolicy', 'Bypass')
    if ($Hidden) { $parts += @('-WindowStyle', 'Hidden') }
    $parts += @('-File', ('"{0}"' -f $ScriptPath))
    if ($IntervalSeconds -ne 60) { $parts += @('-IntervalSeconds', $IntervalSeconds) }
    if ($Minutes -ne 0)          { $parts += @('-Minutes', $Minutes) }
    if ($Quiet)                  { $parts += '-Quiet' }
    if ($SystemOnly)             { $parts += '-SystemOnly' }
    if ($AllMicrosoftApps)       { $parts += '-AllMicrosoftApps' }
    return ($parts -join ' ')
}

# Microsoft desktop apps that -AllMicrosoftApps nudges per-window so they stay
# non-idle even when backgrounded. Process names are lowercase, without ".exe".
$script:MicrosoftAppProcessNames = @(
    'outlook',   # Outlook
    'teams',     # Teams (classic client)
    'ms-teams',  # Teams (new client)
    'onenote',   # OneNote
    'winword',   # Word
    'excel',     # Excel
    'powerpnt',  # PowerPoint
    'msaccess',  # Access
    'mspub',     # Publisher
    'visio',     # Visio
    'winproj',   # Project
    'lync',      # Skype for Business
    'onedrive',  # OneDrive
    'msedge'     # Edge (M365 web apps)
)

function Get-MicrosoftAppProcessNames {
    return $script:MicrosoftAppProcessNames
}

# True when a process name is a targeted Microsoft app. Case-insensitive and
# tolerant of an optional ".exe" suffix so it matches Get-Process output and
# raw image names alike.
function Test-IsMicrosoftApp {
    param([string]$ProcessName)
    if ([string]::IsNullOrWhiteSpace($ProcessName)) { return $false }
    $name = $ProcessName.Trim().ToLower()
    if ($name.EndsWith('.exe')) { $name = $name.Substring(0, $name.Length - 4) }
    return ($script:MicrosoftAppProcessNames -contains $name)
}
