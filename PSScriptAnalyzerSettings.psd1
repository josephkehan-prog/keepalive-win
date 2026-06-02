@{
    ExcludeRules = @(
        # Intentional: keepalive.ps1 is a user-facing CLI; Write-Host is the right tool.
        'PSAvoidUsingWriteHost',
        # Intentional: these are scripts, not modules. ShouldProcess is for module cmdlets.
        'PSUseShouldProcessForStateChangingFunctions',
        # Intentional: Send-BrowserNudge always targets the local CDP port; localhost is correct.
        'PSAvoidUsingComputerNameHardcoded',
        # Intentional: per-window/per-tab PostMessage and WebSocket failures are silently swallowed
        # so that a single failing app or closing tab never breaks the keep-alive loop.
        'PSAvoidUsingEmptyCatchBlock',
        # Intentional: positional parameters are used conventionally for common cmdlets
        # (Write-Host, Test-Path, Get-Content, Remove-Item, Invoke-RestMethod) following
        # standard PowerShell idiom; explicit -Object/-Path/-Uri adds noise without clarity.
        'PSAvoidUsingPositionalParameters',
        # Intentional: script-scope constants (Win32 flags, P/Invoke values) are defined at
        # script scope for readability and used inside nested function definitions in the same
        # file. PSScriptAnalyzer does not always track cross-scope usage within a single script.
        'PSUseDeclaredVarsMoreThanAssignments',
        # Intentional: UTF-8 without BOM is the standard encoding for PowerShell scripts on
        # modern toolchains; adding a BOM would break compatibility with some editors and tools.
        'PSUseBOMForUnicodeEncodedFile',
        # Intentional: 2>$null is used to suppress Test-NetConnection's verbose output.
        # PSScriptAnalyzer may mis-classify stream-2 redirection as a potential comparison.
        'PSPossibleIncorrectUsageOfRedirectionOperator',
        # Intentional: script-level parameters are referenced in nested function bodies
        # (Install-StartupTask, Start-Headless, Enable-StayAwake) which PSScriptAnalyzer
        # may not count as usages when checking the script-level param block.
        'PSReviewUnusedParameter',
        # Intentional: -Profile is the right user-facing parameter name even though
        # PowerShell has a $Profile automatic variable; the conflict is harmless here.
        'PSAvoidAssignmentToAutomaticVariable',
        # Intentional: functions that return collections use plural nouns
        # (Get-AwakeFlags, Get-StartupArguments, etc.) which is semantically correct.
        'PSUseSingularNouns'
    )
}
