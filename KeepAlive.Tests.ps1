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
    It 'composes ES_CONTINUOUS|ES_SYSTEM_REQUIRED|ES_DISPLAY_REQUIRED as 0x80000003' {
        # 0x80000000 | 0x1 | 0x2 = 2147483651, must survive as an unsigned 32-bit value
        Get-AwakeFlags | Should Be ([uint32]2147483651)
    }
    It 'returns a uint32 (not a sign-flipped negative int)' {
        (Get-AwakeFlags) -gt 0 | Should Be $true
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
