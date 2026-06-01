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
    # Invariant culture: a culture-sensitive ToLower() (e.g. Turkish 'I' -> dotless 'ı')
    # would break matching for ASCII image names like VISIO/LYNC.
    $name = $ProcessName.Trim().ToLowerInvariant()
    if ($name.EndsWith('.exe')) { $name = $name.Substring(0, $name.Length - 4) }
    return ($script:MicrosoftAppProcessNames -contains $name)
}

# --- Run loop (injectable for testing) ----------------------------------------
# All side-effecting operations (Win32 calls) are passed as script blocks so
# the loop can be unit-tested without P/Invoke. -Tick defaults to Start-Sleep 1s;
# pass {} in tests to skip real waiting. -Clock defaults to Get-Date; pass a
# controlled clock to simulate time passage.

function Invoke-KeepAlive {
    param(
        [int]$IntervalSeconds      = 60,
        [int]$Minutes              = 0,
        [switch]$Quiet,
        [string]$ModeSuffix        = '',
        [scriptblock]$Enable       = $null,
        [scriptblock]$Restore      = $null,
        [scriptblock]$Nudge        = $null,
        [scriptblock]$AppNudge     = $null,
        [scriptblock]$BrowserNudge = $null,
        [scriptblock]$StopWhen     = $null,
        [scriptblock]$Clock        = { Get-Date },
        [scriptblock]$Tick         = $null
    )
    $start   = & $Clock
    $endTime = Get-EndTime -Start $start -Minutes $Minutes
    $banner  = if ($endTime) {
        "Keeping awake$ModeSuffix until $($endTime.ToString('HH:mm:ss')). Press Ctrl+C to stop."
    } else {
        "Keeping awake$ModeSuffix. Press Ctrl+C to stop."
    }
    Write-Host $banner
    try {
        if ($Enable) { & $Enable }
        while ($true) {
            if (Test-ShouldStop -Now (& $Clock) -EndTime $endTime) { break }
            if ($StopWhen -and (& $StopWhen))                      { break }
            if ($Nudge)        { & $Nudge }
            if ($AppNudge)     { & $AppNudge }
            if ($BrowserNudge) { & $BrowserNudge }
            if (-not $Quiet) {
                Write-Host ("[{0}] awake - next nudge in {1}s" -f (& $Clock).ToString('HH:mm:ss'), $IntervalSeconds)
            }
            # Sleep in 1s slices so Ctrl+C and -Minutes stay responsive.
            for ($i = 0; $i -lt $IntervalSeconds; $i++) {
                if (Test-ShouldStop -Now (& $Clock) -EndTime $endTime) { break }
                if ($StopWhen -and (& $StopWhen))                      { break }
                if ($Tick) { & $Tick } else { Start-Sleep -Seconds 1 }
            }
        }
    }
    finally {
        if ($Restore) { & $Restore }
        Write-Host "Stopped - normal power behavior restored."
    }
}

# --- PID file (headless process lifecycle) ------------------------------------

function Get-PidFilePath {
    return (Join-Path $env:TEMP 'keepalive.pid')
}

# --- Named profiles (keepalive.json) ------------------------------------------

function Read-ProfileConfig {
    param([string]$ConfigPath)
    if (-not (Test-Path $ConfigPath)) { return $null }
    try {
        return (Get-Content $ConfigPath -Raw -ErrorAction Stop | ConvertFrom-Json).profiles
    } catch { return $null }
}

function Get-ProfileSettings {
    param([object]$Profiles, [string]$ProfileName)
    if ($null -eq $Profiles -or [string]::IsNullOrWhiteSpace($ProfileName)) { return $null }
    $prop = $Profiles.PSObject.Properties[$ProfileName]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

# --- Browser tab keep-alive (CDP) URL helpers ---------------------------------

$script:M365UrlPatterns = @(
    'outlook\.office',
    'teams\.microsoft',
    '\.sharepoint\.com',
    '\.office\.com',
    'onedrive\.live\.com',
    '\.microsoftonline\.com'
)

function Get-M365UrlPatterns { return $script:M365UrlPatterns }

function Test-IsM365Url {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) { return $false }
    foreach ($pattern in $script:M365UrlPatterns) {
        if ($Url -match $pattern) { return $true }
    }
    return $false
}

function Select-M365Tabs {
    param([object[]]$Tabs)
    if ($null -eq $Tabs) { return @() }
    return @($Tabs | Where-Object { Test-IsM365Url -Url $_.url })
}
