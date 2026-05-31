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
