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
        'PSAvoidUsingPositionalParameters'
    )
}
