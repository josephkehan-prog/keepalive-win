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
    It 'composes every option in launcher-then-script order' {
        Get-StartupArguments -ScriptPath $path -IntervalSeconds 30 -Minutes 90 -Quiet -SystemOnly -Hidden |
            Should Be '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Tools\keepalive.ps1" -IntervalSeconds 30 -Minutes 90 -Quiet -SystemOnly'
    }
}
