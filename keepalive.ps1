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
    so you can close the terminal and keep the machine awake. Implies -Quiet. Use -Stop
    to end it gracefully, or -Status to check whether it is running.

.PARAMETER Stop
    Stop a background process started with -Headless by reading the PID file and
    terminating it, then exit.

.PARAMETER Status
    Show whether the logon task (-Install) is registered and whether a -Headless
    background process is currently running, then exit.

.PARAMETER WatchProcess
    Auto-stop keepalive when the named process (e.g. 'Teams') is no longer running.
    Checked every interval. Useful when you only need to stay awake while a specific
    app is open.

.PARAMETER Profile
    Load default settings from a named profile in keepalive.json (same directory as
    this script). CLI flags override profile values. Example profiles: 'meeting',
    'focus'. Create keepalive.json to define your own presets.

.PARAMETER AllMicrosoftApps
    Also keep running Microsoft desktop apps (Outlook, Teams, Word, Excel, OneNote,
    Edge, etc.) non-idle even when they are minimized/backgrounded, by posting a
    harmless no-op window message to each one every interval. Does not steal focus.

.PARAMETER BrowserKeepAlive
    Periodically send a harmless F15 key event to M365 tabs in a Chrome or Edge
    instance launched with --remote-debugging-port=9222, resetting their tab-level
    idle timer. Addresses server-side M365 session timeouts that are not fixed by the
    OS-level keep-awake alone (see Step 5 in plans/keepalive-cli-anti-idle.md).

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

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Status
    Shows whether the logon task is installed and whether a headless process is running.

.EXAMPLE
    pwsh -File .\keepalive.ps1 -Profile meeting
    Loads the 'meeting' preset from keepalive.json (e.g. 120 min + SystemOnly).

.EXAMPLE
    pwsh -File .\keepalive.ps1 -WatchProcess teams
    Stays awake until Teams exits, then stops automatically.
#>
[CmdletBinding()]
param(
    [int]$IntervalSeconds    = 60,
    [int]$Minutes            = 0,
    [switch]$Quiet,
    [switch]$SystemOnly,
    [switch]$AllMicrosoftApps,
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Headless,
    [switch]$Stop,
    [switch]$Status,
    [string]$WatchProcess    = '',
    [string]$Profile         = '',
    [switch]$BrowserKeepAlive
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

# Apply named profile defaults; explicit CLI flags always win.
if ($Profile) {
    $configPath = Join-Path $PSScriptRoot 'keepalive.json'
    $profiles   = Read-ProfileConfig -ConfigPath $configPath
    $preset     = Get-ProfileSettings -Profiles $profiles -ProfileName $Profile
    if ($null -eq $preset) {
        Write-Error "Profile '$Profile' not found in '$configPath'."
        exit 1
    }
    if (-not $PSBoundParameters.ContainsKey('IntervalSeconds') -and $preset.PSObject.Properties['IntervalSeconds']) {
        $IntervalSeconds = [int]$preset.IntervalSeconds
    }
    if (-not $PSBoundParameters.ContainsKey('Minutes') -and $preset.PSObject.Properties['Minutes']) {
        $Minutes = [int]$preset.Minutes
    }
    if (-not $PSBoundParameters.ContainsKey('Quiet') -and $preset.PSObject.Properties['Quiet']) {
        $Quiet = [bool]$preset.Quiet
    }
    if (-not $PSBoundParameters.ContainsKey('SystemOnly') -and $preset.PSObject.Properties['SystemOnly']) {
        $SystemOnly = [bool]$preset.SystemOnly
    }
    if (-not $PSBoundParameters.ContainsKey('AllMicrosoftApps') -and $preset.PSObject.Properties['AllMicrosoftApps']) {
        $AllMicrosoftApps = [bool]$preset.AllMicrosoftApps
    }
}

# --- Run-at-logon (-Install / -Uninstall) and background (-Headless) ----------

function Get-PwshPath {
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
    $taskName = Get-StartupTaskName
    if (-not (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)) {
        return $false
    }
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    return $true
}

function Start-Headless {
    $arguments = Get-StartupArguments -ScriptPath $PSCommandPath `
        -IntervalSeconds $IntervalSeconds -Minutes $Minutes -Quiet `
        -SystemOnly:$SystemOnly -AllMicrosoftApps:$AllMicrosoftApps -Hidden
    $proc = Start-Process -FilePath (Get-PwshPath) -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Set-Content -Path (Get-PidFilePath) -Value $proc.Id -Encoding ASCII
}

function Stop-HeadlessProcess {
    $pidFile = Get-PidFilePath
    if (-not (Test-Path $pidFile)) { return $false }
    $storedPid = [int](Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
    $proc = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $storedPid -Force -ErrorAction SilentlyContinue }
    Remove-Item $pidFile -ErrorAction SilentlyContinue
    return $true
}

function Get-KeepAliveStatus {
    $task   = Get-ScheduledTask -TaskName (Get-StartupTaskName) -ErrorAction SilentlyContinue
    $bgProc = $null
    $pidFile = Get-PidFilePath
    if (Test-Path $pidFile) {
        $storedPid = [int](Get-Content $pidFile -Raw -ErrorAction SilentlyContinue).Trim()
        $bgProc = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
    }
    return [pscustomobject]@{ ScheduledTask = $task; HeadlessProcess = $bgProc }
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

if ($Stop) {
    if (Stop-HeadlessProcess) {
        Write-Host "Stopped the background keepalive process."
    } else {
        Write-Host "No background keepalive process found (no PID file at '$(Get-PidFilePath)')."
    }
    exit 0
}

if ($Status) {
    $s = Get-KeepAliveStatus
    if ($s.ScheduledTask) {
        Write-Host "Logon task '$(Get-StartupTaskName)': $($s.ScheduledTask.State)"
    } else {
        Write-Host "No logon task installed."
    }
    if ($s.HeadlessProcess) {
        $uptime = (Get-Date) - $s.HeadlessProcess.StartTime
        Write-Host ("Headless process: PID {0}, running for {1:0} min" -f $s.HeadlessProcess.Id, $uptime.TotalMinutes)
    } else {
        Write-Host "No headless process running."
    }
    exit 0
}

if ($Headless) {
    Start-Headless
    Write-Host "Keep-awake started in the background. Use 'keepalive -Stop' to stop it, or 'keepalive -Status' to check."
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
    # Post WM_NULL to each Microsoft app's main window — async, never steals focus.
    foreach ($proc in Get-Process -ErrorAction SilentlyContinue) {
        if (-not (Test-IsMicrosoftApp -ProcessName $proc.ProcessName)) { continue }
        $hWnd = $proc.MainWindowHandle
        if ($hWnd -ne [IntPtr]::Zero) {
            try { [void][KeepAlive.Native]::PostMessage($hWnd, $WM_NULL, [IntPtr]::Zero, [IntPtr]::Zero) } catch { }
        }
    }
}
function Send-BrowserNudge {
    # Send an F15 key event to each M365 tab via Chrome/Edge remote debugging (CDP).
    # Requires the browser to be launched with --remote-debugging-port=9222.
    param([int]$DebugPort = 9222)
    $conn = Test-NetConnection -ComputerName localhost -Port $DebugPort `
        -InformationLevel Quiet -WarningAction SilentlyContinue 2>$null
    if (-not $conn) { return }
    try {
        $tabs     = Invoke-RestMethod "http://localhost:$DebugPort/json" -ErrorAction Stop
        $m365Tabs = Select-M365Tabs -Tabs $tabs
        foreach ($tab in $m365Tabs) {
            if (-not $tab.webSocketDebuggerUrl) { continue }
            try {
                $ws  = [System.Net.WebSockets.ClientWebSocket]::new()
                $cts = [System.Threading.CancellationTokenSource]::new(3000)
                $ws.ConnectAsync([Uri]$tab.webSocketDebuggerUrl, $cts.Token).Wait()
                $cmd   = '{"id":1,"method":"Input.dispatchKeyEvent","params":{"type":"keyDown","key":"F15","code":"F15","keyCode":126}}'
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($cmd)
                $seg   = [System.ArraySegment[byte]]::new($bytes)
                $ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()
                $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, '', $cts.Token).Wait()
                $ws.Dispose()
                $cts.Dispose()
            } catch { }
        }
    } catch { }
}

if ($BrowserKeepAlive) {
    $portOpen = Test-NetConnection -ComputerName localhost -Port 9222 `
        -InformationLevel Quiet -WarningAction SilentlyContinue 2>$null
    if (-not $portOpen) {
        Write-Warning "No Chrome/Edge debug port found at localhost:9222. Launch your browser with --remote-debugging-port=9222 to enable browser tab keep-alive."
    }
}

$mode              = if ($SystemOnly)       { " (display may sleep)" } else { "" }
$appNudgeBlock     = if ($AllMicrosoftApps) { { Send-AppNudge } }     else { $null }
$browserNudgeBlock = if ($BrowserKeepAlive) { { Send-BrowserNudge } } else { $null }
$stopWhenBlock     = if ($WatchProcess)     {
    $proc = $WatchProcess
    { -not (Get-Process -Name $proc -ErrorAction SilentlyContinue) }.GetNewClosure()
} else { $null }

Invoke-KeepAlive `
    -IntervalSeconds $IntervalSeconds `
    -Minutes         $Minutes `
    -Quiet:$Quiet `
    -ModeSuffix      $mode `
    -Enable          { Enable-StayAwake } `
    -Restore         { Restore-Power } `
    -Nudge           { Send-Nudge } `
    -AppNudge        $appNudgeBlock `
    -BrowserNudge    $browserNudgeBlock `
    -StopWhen        $stopWhenBlock
