<#
.SYNOPSIS
    Keeps Windows awake so M365 web tabs (Outlook / SharePoint / Teams) don't auto-log-out
    from sleep, screen-lock, or idle.

.DESCRIPTION
    While running, this blocks system sleep + display-off (SetThreadExecutionState) and
    sends a harmless F15 keypress every -IntervalSeconds to reset the Windows idle timer.
    Press Ctrl+C to stop; normal power behavior is always restored on exit.

    This keeps the OS active. It does NOT bypass authentication or an admin-enforced
    server-side session timeout (see plans/keepalive-cli-anti-idle.md, Step 5).

.PARAMETER IntervalSeconds
    Seconds between idle-timer nudges. Minimum 10. Default 60.

.PARAMETER Minutes
    Auto-stop after this many minutes. 0 (default) = run until Ctrl+C.

.PARAMETER Quiet
    Suppress the periodic status line.

.EXAMPLE
    pwsh -File .\keepalive.ps1
    Keeps awake until you press Ctrl+C.

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Minutes 90 -Quiet
    Stays awake for 90 minutes, no status output.
#>
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60,
    [int]$Minutes = 0,
    [switch]$Quiet
)

. "$PSScriptRoot\KeepAlive.Core.ps1"

if (-not (Test-IntervalValid -IntervalSeconds $IntervalSeconds)) {
    Write-Error "IntervalSeconds must be >= 10 (got $IntervalSeconds)."
    exit 1
}

Add-Type -Namespace KeepAlive -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
'@

$VK_F15          = [byte]0x7E
$KEYEVENTF_KEYUP = [uint32]0x2
$ES_CONTINUOUS   = [uint32]2147483648

function Enable-StayAwake { [void][KeepAlive.Native]::SetThreadExecutionState((Get-AwakeFlags)) }
function Restore-Power    { [void][KeepAlive.Native]::SetThreadExecutionState($ES_CONTINUOUS) }
function Send-Nudge {
    [KeepAlive.Native]::keybd_event($VK_F15, 0, 0, [UIntPtr]::Zero)
    [KeepAlive.Native]::keybd_event($VK_F15, 0, $KEYEVENTF_KEYUP, [UIntPtr]::Zero)
}

$start   = Get-Date
$endTime = Get-EndTime -Start $start -Minutes $Minutes

$banner = if ($endTime) { "Keeping awake until $($endTime.ToString('HH:mm:ss')). Press Ctrl+C to stop." }
          else          { "Keeping awake. Press Ctrl+C to stop." }
Write-Host $banner

try {
    Enable-StayAwake
    while ($true) {
        if (Test-ShouldStop -Now (Get-Date) -EndTime $endTime) { break }
        Send-Nudge
        if (-not $Quiet) {
            Write-Host ("[{0}] awake - next nudge in {1}s" -f (Get-Date).ToString('HH:mm:ss'), $IntervalSeconds)
        }
        # Sleep in 1s slices so Ctrl+C and -Minutes stay responsive.
        for ($i = 0; $i -lt $IntervalSeconds; $i++) {
            if (Test-ShouldStop -Now (Get-Date) -EndTime $endTime) { break }
            Start-Sleep -Seconds 1
        }
    }
}
finally {
    Restore-Power
    Write-Host "Stopped - normal power behavior restored."
}
