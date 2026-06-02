# KeepAlive.Tests.ps1 — Pester 3.4 tests for the pure keepalive logic.
# Run: Invoke-Pester -Path .\KeepAlive.Tests.ps1

. "$PSScriptRoot\KeepAlive.Core.ps1"

Describe 'Test-IntervalValid' {
    It 'accepts the minimum allowed interval (10s)' {
        Test-IntervalValid -IntervalSeconds 10 | Should Be $true
    }
    It 'accepts a normal interval (60s)' {
        Test-IntervalValid -IntervalSeconds 60 | Should Be $true
    }
    It 'rejects an interval below the minimum (5s)' {
        Test-IntervalValid -IntervalSeconds 5 | Should Be $false
    }
    It 'rejects zero' {
        Test-IntervalValid -IntervalSeconds 0 | Should Be $false
    }
}

Describe 'Get-EndTime' {
    $start = [datetime]'2026-05-31T12:00:00'

    It 'returns $null when Minutes is 0 (run forever)' {
        Get-EndTime -Start $start -Minutes 0 | Should Be $null
    }
    It 'returns $null when Minutes is negative' {
        Get-EndTime -Start $start -Minutes -5 | Should Be $null
    }
    It 'returns start + N minutes when Minutes > 0' {
        Get-EndTime -Start $start -Minutes 30 | Should Be ([datetime]'2026-05-31T12:30:00')
    }
}

Describe 'Get-AwakeFlags' {
    It 'composes ES_CONTINUOUS|ES_SYSTEM_REQUIRED|ES_DISPLAY_REQUIRED as 0x80000003 by default' {
        # 0x80000000 | 0x1 | 0x2 = 2147483651, must survive as an unsigned 32-bit value
        Get-AwakeFlags | Should Be ([uint32]2147483651)
    }
    It 'returns a uint32 (not a sign-flipped negative int)' {
        (Get-AwakeFlags) -gt 0 | Should Be $true
    }
    It 'keeps the system awake but lets the display sleep (0x80000001)' {
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED = 2147483649
        Get-AwakeFlags -KeepDisplayOn $false | Should Be ([uint32]2147483649)
    }
    It 'keeps the display on but lets the system sleep (0x80000002)' {
        # ES_CONTINUOUS | ES_DISPLAY_REQUIRED = 2147483650
        Get-AwakeFlags -KeepSystemAwake $false | Should Be ([uint32]2147483650)
    }
    It 'returns just ES_CONTINUOUS when both are cleared (0x80000000)' {
        Get-AwakeFlags -KeepSystemAwake $false -KeepDisplayOn $false | Should Be ([uint32]2147483648)
    }
}

Describe 'Get-CatFrame' {
    It 'returns the eyes-open cat for tick 0' {
        Get-CatFrame -Counter 0 | Should Be '=^.^='
    }
    It 'returns the blinking cat for tick 1' {
        Get-CatFrame -Counter 1 | Should Be '=^-^='
    }
    It 'wraps back to the first frame after the last' {
        Get-CatFrame -Counter 2 | Should Be '=^.^='
    }
    It 'alternates frames on consecutive ticks' {
        (Get-CatFrame -Counter 3) | Should Be '=^-^='
    }
    It 'defaults to the eyes-open cat with no counter' {
        Get-CatFrame | Should Be '=^.^='
    }
    It 'handles a negative counter without throwing' {
        Get-CatFrame -Counter -1 | Should Be '=^-^='
    }
    It 'returns an ASCII-only string (no non-ASCII bytes)' {
        $frame = Get-CatFrame -Counter 0
        ($frame.ToCharArray() | Where-Object { [int]$_ -gt 127 }).Count | Should Be 0
    }
}

Describe 'Test-ShouldStop' {
    $now = [datetime]'2026-05-31T12:00:00'

    It 'never stops when EndTime is $null' {
        Test-ShouldStop -Now $now -EndTime $null | Should Be $false
    }
    It 'does not stop before EndTime' {
        Test-ShouldStop -Now $now -EndTime ([datetime]'2026-05-31T12:30:00') | Should Be $false
    }
    It 'stops exactly at EndTime' {
        Test-ShouldStop -Now $now -EndTime $now | Should Be $true
    }
    It 'stops after EndTime' {
        Test-ShouldStop -Now $now -EndTime ([datetime]'2026-05-31T11:59:00') | Should Be $true
    }
}

Describe 'Get-StartupTaskName' {
    It 'returns the stable task name used by -Install/-Uninstall' {
        Get-StartupTaskName | Should Be 'KeepAlive'
    }
}

Describe 'Get-StartupArguments' {
    $path = 'C:\Tools\keepalive.ps1'

    It 'emits only the launcher defaults for a plain relaunch' {
        Get-StartupArguments -ScriptPath $path |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1"'
    }
    It 'quotes a script path that contains spaces' {
        Get-StartupArguments -ScriptPath 'C:\My Tools\keepalive.ps1' |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\My Tools\keepalive.ps1"'
    }
    It 'appends -Quiet when requested' {
        Get-StartupArguments -ScriptPath $path -Quiet |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1" -Quiet'
    }
    It 'includes -IntervalSeconds only when it differs from the default 60' {
        Get-StartupArguments -ScriptPath $path -IntervalSeconds 30 |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1" -IntervalSeconds 30'
    }
    It 'omits -IntervalSeconds when it equals the default 60' {
        Get-StartupArguments -ScriptPath $path -IntervalSeconds 60 |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1"'
    }
    It 'includes -Minutes only when non-zero' {
        Get-StartupArguments -ScriptPath $path -Minutes 90 |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1" -Minutes 90'
    }
    It 'inserts -WindowStyle Hidden before -File when -Hidden is set' {
        Get-StartupArguments -ScriptPath $path -Hidden |
            Should Be '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Tools\keepalive.ps1"'
    }
    It 'appends -SystemOnly when requested' {
        Get-StartupArguments -ScriptPath $path -SystemOnly |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1" -SystemOnly'
    }
    It 'appends -AllMicrosoftApps when requested' {
        Get-StartupArguments -ScriptPath $path -AllMicrosoftApps |
            Should Be '-NoProfile -ExecutionPolicy Bypass -File "C:\Tools\keepalive.ps1" -AllMicrosoftApps'
    }
    It 'composes every option in launcher-then-script order' {
        Get-StartupArguments -ScriptPath $path -IntervalSeconds 30 -Minutes 90 -Quiet -SystemOnly -AllMicrosoftApps -Hidden |
            Should Be '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Tools\keepalive.ps1" -IntervalSeconds 30 -Minutes 90 -Quiet -SystemOnly -AllMicrosoftApps'
    }
}

Describe 'Get-MicrosoftAppProcessNames' {
    It 'returns a non-empty list of targeted Microsoft app process names' {
        (Get-MicrosoftAppProcessNames).Count -gt 0 | Should Be $true
    }
    It 'includes the core M365 desktop apps' {
        $names = Get-MicrosoftAppProcessNames
        $names -contains 'outlook' | Should Be $true
        $names -contains 'teams'   | Should Be $true
        $names -contains 'excel'   | Should Be $true
    }
}

Describe 'Test-IsMicrosoftApp' {
    It 'matches a known app regardless of case' {
        Test-IsMicrosoftApp -ProcessName 'OUTLOOK' | Should Be $true
    }
    It 'tolerates an .exe suffix' {
        Test-IsMicrosoftApp -ProcessName 'WINWORD.EXE' | Should Be $true
    }
    It 'matches the new Teams client name (ms-teams)' {
        Test-IsMicrosoftApp -ProcessName 'ms-teams' | Should Be $true
    }
    It 'rejects a non-Microsoft process' {
        Test-IsMicrosoftApp -ProcessName 'notepad' | Should Be $false
    }
    It 'rejects empty or whitespace input' {
        Test-IsMicrosoftApp -ProcessName '   ' | Should Be $false
    }
}

Describe 'Invoke-KeepAlive' {
    It 'calls Enable at loop start' {
        $script:enableCalled = $false
        Invoke-KeepAlive `
            -StopWhen { $true } `
            -Enable   { $script:enableCalled = $true } `
            -Restore {} -Clock { Get-Date } -Tick {}
        $script:enableCalled | Should Be $true
    }
    It 'calls Restore in finally even when Enable throws' {
        $script:restoreCalled = $false
        try {
            Invoke-KeepAlive `
                -Enable  { throw 'simulated error' } `
                -Restore { $script:restoreCalled = $true } `
                -Clock { Get-Date } -Tick {}
        } catch { }
        $script:restoreCalled | Should Be $true
    }
    It 'calls Restore on normal exit' {
        $script:restoreCalled = $false
        Invoke-KeepAlive `
            -StopWhen { $true } `
            -Enable   {} `
            -Restore  { $script:restoreCalled = $true } `
            -Clock { Get-Date } -Tick {}
        $script:restoreCalled | Should Be $true
    }
    It 'does not call Nudge when StopWhen stops the loop immediately' {
        $script:nudgeCalled = $false
        Invoke-KeepAlive `
            -StopWhen { $true } `
            -Nudge    { $script:nudgeCalled = $true } `
            -Enable {} -Restore {} -Clock { Get-Date } -Tick {}
        $script:nudgeCalled | Should Be $false
    }
    It 'calls Nudge once when loop runs one iteration before auto-stopping' {
        $script:nudgeCount = 0
        $script:clk = 0
        Invoke-KeepAlive `
            -Minutes 1 `
            -Clock {
                switch ($script:clk++) {
                    0       { [datetime]'2026-01-01T12:00:00' }
                    1       { [datetime]'2026-01-01T12:00:30' }
                    default { [datetime]'2026-01-01T12:02:00' }
                }
            } `
            -Nudge  { $script:nudgeCount++ } `
            -Enable {} -Restore {} -Tick {}
        $script:nudgeCount | Should Be 1
    }
    It 'does not throw when Quiet is set' {
        $script:clk = 0
        {
            Invoke-KeepAlive -Quiet `
                -StopWhen { $true } `
                -Enable {} -Restore {} -Clock { Get-Date } -Tick {}
        } | Should Not Throw
    }
    It 'does not call AppNudge when AppNudge is null' {
        $script:appNudgeCalled = $false
        Invoke-KeepAlive `
            -StopWhen { $true } `
            -AppNudge $null `
            -Enable {} -Restore {} -Clock { Get-Date } -Tick {}
        $script:appNudgeCalled | Should Be $false
    }
    It 'calls AppNudge when provided' {
        $script:appNudgeCalled = $false
        $script:clk = 0
        Invoke-KeepAlive `
            -Minutes 1 `
            -Clock {
                switch ($script:clk++) {
                    0       { [datetime]'2026-01-01T12:00:00' }
                    1       { [datetime]'2026-01-01T12:00:30' }
                    default { [datetime]'2026-01-01T12:02:00' }
                }
            } `
            -AppNudge { $script:appNudgeCalled = $true } `
            -Enable {} -Restore {} -Nudge {} -Tick {}
        $script:appNudgeCalled | Should Be $true
    }
}

Describe 'Get-PidFilePath' {
    It 'returns a path ending in keepalive.pid' {
        (Get-PidFilePath) | Should Match 'keepalive\.pid$'
    }
    It 'returns a path under TEMP' {
        (Get-PidFilePath).StartsWith($env:TEMP) | Should Be $true
    }
}

Describe 'Read-ProfileConfig' {
    It 'returns $null when the config file does not exist' {
        Read-ProfileConfig -ConfigPath 'C:\nonexistent\keepalive.json' | Should Be $null
    }
    It 'returns $null for malformed JSON' {
        $tmp = Join-Path $env:TEMP 'keepalive-bad.json'
        Set-Content $tmp -Value 'NOT JSON' -Encoding UTF8
        $result = Read-ProfileConfig -ConfigPath $tmp
        Remove-Item $tmp -ErrorAction SilentlyContinue
        $result | Should Be $null
    }
    It 'parses profiles from a valid config file' {
        $tmp = Join-Path $env:TEMP 'keepalive-test.json'
        Set-Content $tmp -Value '{"profiles":{"meeting":{"Minutes":120,"SystemOnly":true}}}' -Encoding UTF8
        $result = Read-ProfileConfig -ConfigPath $tmp
        Remove-Item $tmp -ErrorAction SilentlyContinue
        $result | Should Not Be $null
    }
}

Describe 'Get-ProfileSettings' {
    $profiles = '{"meeting":{"Minutes":120},"focus":{"Quiet":true}}' | ConvertFrom-Json

    It 'returns the settings for a known profile' {
        $result = Get-ProfileSettings -Profiles $profiles -ProfileName 'meeting'
        $result.Minutes | Should Be 120
    }
    It 'returns $null for an unknown profile name' {
        Get-ProfileSettings -Profiles $profiles -ProfileName 'unknown' | Should Be $null
    }
    It 'returns $null when Profiles is $null' {
        Get-ProfileSettings -Profiles $null -ProfileName 'meeting' | Should Be $null
    }
    It 'returns $null when ProfileName is empty' {
        Get-ProfileSettings -Profiles $profiles -ProfileName '' | Should Be $null
    }
}

Describe 'Test-IsM365Url' {
    It 'matches Outlook web' {
        Test-IsM365Url 'https://outlook.office365.com/mail/' | Should Be $true
    }
    It 'matches Teams web' {
        Test-IsM365Url 'https://teams.microsoft.com/v2/' | Should Be $true
    }
    It 'matches SharePoint' {
        Test-IsM365Url 'https://contoso.sharepoint.com/sites/hr' | Should Be $true
    }
    It 'matches Office.com' {
        Test-IsM365Url 'https://www.office.com' | Should Be $true
    }
    It 'does not match non-M365 URLs' {
        Test-IsM365Url 'https://google.com' | Should Be $false
    }
    It 'returns false for empty string' {
        Test-IsM365Url '' | Should Be $false
    }
}

Describe 'Select-M365Tabs' {
    It 'returns only M365 tabs from a mixed list' {
        $tabs = @(
            [pscustomobject]@{ url = 'https://outlook.office365.com/mail/' },
            [pscustomobject]@{ url = 'https://google.com' },
            [pscustomobject]@{ url = 'https://contoso.sharepoint.com/sites/hr' }
        )
        (Select-M365Tabs -Tabs $tabs).Count | Should Be 2
    }
    It 'returns empty array for null input' {
        (Select-M365Tabs -Tabs $null).Count | Should Be 0
    }
    It 'returns empty array when no tabs match M365 patterns' {
        $tabs = @([pscustomobject]@{ url = 'https://github.com' })
        (Select-M365Tabs -Tabs $tabs).Count | Should Be 0
    }
}
