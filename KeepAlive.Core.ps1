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
    # ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x1) | ES_DISPLAY_REQUIRED (0x2)
    $ES_CONTINUOUS       = [uint32]2147483648
    $ES_SYSTEM_REQUIRED  = [uint32]1
    $ES_DISPLAY_REQUIRED = [uint32]2
    return [uint32]($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED)
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
        [switch]$Hidden
    )
    $parts = @('-NoProfile', '-ExecutionPolicy', 'Bypass')
    if ($Hidden) { $parts += @('-WindowStyle', 'Hidden') }
    $parts += @('-File', ('"{0}"' -f $ScriptPath))
    if ($IntervalSeconds -ne 60) { $parts += @('-IntervalSeconds', $IntervalSeconds) }
    if ($Minutes -ne 0)          { $parts += @('-Minutes', $Minutes) }
    if ($Quiet)                  { $parts += '-Quiet' }
    return ($parts -join ' ')
}
