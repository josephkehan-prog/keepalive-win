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

.PARAMETER SystemOnly
    Keep the machine awake from sleep but allow the display/monitor to turn off.
    Prevents sleep/idle logout while still letting the screen power down. By default
    both system sleep and display-off are blocked.

.PARAMETER Install
    Register a "run at logon" scheduled task ('KeepAlive') that relaunches this CLI
    automatically, then exit. Any -IntervalSeconds / -Minutes / -Quiet / -SystemOnly /
    -AllMicrosoftApps flags given alongside -Install are baked into the task. The task
    runs with a hidden window. If -Install and -Uninstall are both given it is an error.

.PARAMETER Uninstall
    Remove the 'KeepAlive' logon task, then exit.

.PARAMETER Headless
    Relaunch this CLI in a hidden, detached background process and return immediately,
    so you can close the terminal and keep the machine awake. Implies -Quiet.

.PARAMETER AllMicrosoftApps
    Also keep running Microsoft desktop apps (Outlook, Teams, Word, Excel, OneNote,
    Edge, etc.) non-idle even when they are minimized/backgrounded, by posting a
    harmless no-op window message to each one every interval. Does not steal focus.

.EXAMPLE
    pwsh -File .\keepalive.ps1
    Keeps awake until you press Ctrl+C.

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Minutes 90 -Quiet
    Stays awake for 90 minutes, no status output.

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Install -Quiet
    Registers a logon task so the tool starts automatically each time you sign in.

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Headless
    Starts keep-awake in the background and returns; close the terminal freely.
#>
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60,
    [int]$Minutes = 0,
    [switch]$Quiet,
    [switch]$SystemOnly,
    [switch]$AllMicrosoftApps,
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Headless
)

. "$PSScriptRoot\KeepAlive.Core.ps1"

if (-not (Test-IntervalValid -IntervalSeconds $IntervalSeconds)) {
    Write-Error "IntervalSeconds must be >= 10 (got $IntervalSeconds)."
    exit 1
}

if ($Install -and $Uninstall) {
    Write-Error "Use either -Install or -Uninstall, not both."
    exit 1
}

# --- Run-at-logon (-Install / -Uninstall) and background (-Headless) ----------
# These re-launch keepalive.ps1 itself; the actual keep-awake work is unchanged.

function Get-PwshPath {
    # Full path to the current PowerShell host, so the task/process is unambiguous.
    return (Get-Process -Id $PID).Path
}

function Install-StartupTask {
    $taskName  = Get-StartupTaskName
    $arguments = Get-StartupArguments -ScriptPath $PSCommandPath `
        -IntervalSeconds $IntervalSeconds -Minutes $Minutes -Quiet:$Quiet `
        -SystemOnly:$SystemOnly -AllMicrosoftApps:$AllMicrosoftApps -Hidden
    $action   = New-ScheduledTaskAction -Execute (Get-PwshPath) -Argument $arguments
    $trigger  = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -Description 'Keep Windows awake to avoid M365 web auto-logout.' -Force | Out-Null
}

function Uninstall-StartupTask {
    # Returns $true if a task was removed, $false if there was nothing to remove,
    # so -Uninstall on a clean machine doesn't surface a scary error.
    $taskName = Get-StartupTaskName
    if (-not (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) {
        return $false
    }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    return $true
}

function Start-Headless {
    # Spawn a detached, hidden copy and let this foreground invocation return.
    $arguments = Get-StartupArguments -ScriptPath $PSCommandPath `
        -IntervalSeconds $IntervalSeconds -Minutes $Minutes -Quiet `
        -SystemOnly:$SystemOnly -AllMicrosoftApps:$AllMicrosoftApps -Hidden
    Start-Process -FilePath (Get-PwshPath) -ArgumentList $arguments -WindowStyle Hidden | Out-Null
}

if ($Uninstall) {
    if (Uninstall-StartupTask) {
        Write-Host "Removed the '$(Get-StartupTaskName)' logon task."
    } else {
        Write-Host "No '$(Get-StartupTaskName)' logon task was installed; nothing to remove."
    }
    exit 0
}

if ($Install) {
    Install-StartupTask
    Write-Host "Installed '$(Get-StartupTaskName)' to run at logon (hidden window)."
    exit 0
}

if ($Headless) {
    Start-Headless
    Write-Host "Keep-awake started in the background. Close this terminal freely; stop it from Task Manager (pwsh) or 'keepalive -Uninstall' if installed."
    exit 0
}

Add-Type -Namespace KeepAlive -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
[DllImport("user32.dll")]
public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
[DllImport("user32.dll")]
public static extern System.IntPtr PostMessage(System.IntPtr hWnd, uint Msg, System.IntPtr wParam, System.IntPtr lParam);
'@

$VK_F15          = [byte]0x7E
$KEYEVENTF_KEYUP = [uint32]0x2
$ES_CONTINUOUS   = [uint32]2147483648
$WM_NULL         = [uint32]0x0000

function Enable-StayAwake { [void][KeepAlive.Native]::SetThreadExecutionState((Get-AwakeFlags -KeepDisplayOn:(-not $SystemOnly))) }
function Restore-Power    { [void][KeepAlive.Native]::SetThreadExecutionState($ES_CONTINUOUS) }
function Send-Nudge {
    [KeepAlive.Native]::keybd_event($VK_F15, 0, 0, [UIntPtr]::Zero)
    [KeepAlive.Native]::keybd_event($VK_F15, 0, $KEYEVENTF_KEYUP, [UIntPtr]::Zero)
}
function Send-AppNudge {
    # Post a harmless no-op (WM_NULL) to each running Microsoft app's main window so
    # it stays non-idle even when backgrounded. PostMessage is async and never steals
    # focus. Per-window failures are ignored so one closing app can't break the loop.
    foreach ($proc in Get-Process -ErrorAction SilentlyContinue) {
        if (-not (Test-IsMicrosoftApp -ProcessName $proc.ProcessName)) { continue }
        $hWnd = $proc.MainWindowHandle
        if ($hWnd -ne [IntPtr]::Zero) {
            try { [void][KeepAlive.Native]::PostMessage($hWnd, $WM_NULL, [IntPtr]::Zero, [IntPtr]::Zero) } catch { }
        }
    }
}

$start   = Get-Date
$endTime = Get-EndTime -Start $start -Minutes $Minutes

$mode   = if ($SystemOnly) { " (display may sleep)" } else { "" }
$banner = if ($endTime) { "Keeping awake$mode until $($endTime.ToString('HH:mm:ss')). Press Ctrl+C to stop." }
          else          { "Keeping awake$mode. Press Ctrl+C to stop." }
Write-Host $banner

try {
    Enable-StayAwake
    while ($true) {
        if (Test-ShouldStop -Now (Get-Date) -EndTime $endTime) { break }
        Send-Nudge
        if ($AllMicrosoftApps) { Send-AppNudge }
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
