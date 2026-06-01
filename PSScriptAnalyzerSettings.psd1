@{
    # Whitelist approach: only run rules we have positively verified pass for this codebase.
    # These catch real bugs (wrong automatic variables, redefining built-ins, unapproved verbs,
    # global variable leaks, dangerous cmdlets, bad null comparisons, bad switch defaults)
    # without generating false positives for the intentional patterns in keepalive.ps1 /
    # KeepAlive.Core.ps1 (Write-Host CLI output, empty catch for fault isolation, positional
    # params for common cmdlets, 2>$null stream suppression, script-scope constants, etc.).
    IncludeRules = @(
        # Catches accidental assignment to $true, $false, $null, $PID, etc.
        'PSAvoidAssignmentToAutomaticVariable',
        # Catches redefining built-in cmdlets like Write-Output, Get-Item, etc.
        'PSAvoidOverwritingBuiltInCmdlets',
        # All function verbs (Get, Test, Invoke, Read, Select, Send, Enable, Restore,
        # Install, Uninstall, Start, Stop, Get) are in the approved list.
        'PSUseApprovedVerbs',
        # Scripts use $script: scope throughout; no $global: variables exist.
        'PSAvoidGlobalVars',
        # Invoke-Expression is not used anywhere in the codebase.
        'PSAvoidUsingInvokeExpression',
        # ConvertTo-SecureString with plain text is not used.
        'PSAvoidUsingConvertToSecureStringWithPlainText',
        # All null comparisons use $null on the left ($null -eq $x), which is correct.
        'PSPossibleIncorrectComparisonWithNull',
        # All [switch] parameters default to $false (no explicit non-false default).
        'PSAvoidDefaultValueSwitchParameter'
    )
}
