@{
    ExcludeRules = @(
        # Intentional: keepalive.ps1 is a user-facing CLI; Write-Host is the right tool.
        'PSAvoidUsingWriteHost',
        # Intentional: these are scripts, not modules. ShouldProcess is for module cmdlets.
        'PSUseShouldProcessForStateChangingFunctions'
    )
}
