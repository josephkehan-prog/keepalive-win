```markdown
# keepalive-win Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the development conventions and workflows used in the `keepalive-win` repository, a TypeScript project (no framework detected) focused on Windows keep-alive functionality. You'll learn how to contribute new features, tune CI pipelines, fix analyzer or locale issues, and follow the project's coding and testing standards.

---

## Coding Conventions

### File Naming

- **PascalCase** is used for file names.
  - Example: `KeepAlive.Core.ps1`, `KeepAlive.Tests.ps1`

### Import Style

- **Relative imports** are used throughout the codebase.
  - Example:
    ```typescript
    import { keepAlive } from './KeepAlive.Core';
    ```

### Export Style

- **Named exports** are preferred.
  - Example:
    ```typescript
    export function keepAlive() { ... }
    ```

### Commit Messages

- **Conventional commit** style is enforced.
- Prefixes include: `ci`, `feat`, `fix`
- Example:
  ```
  feat: add support for custom keep-alive interval
  fix: resolve locale issue in time parsing
  ci: update PSScriptAnalyzer rules for new code style
  ```

---

## Workflows

### Add New Feature with Tests and Docs

**Trigger:** When adding a new user-facing feature or flag to the CLI  
**Command:** `/new-feature`

1. **Implement core logic** in `KeepAlive.Core.ps1` (focus on pure, testable helpers and parameter handling).
2. **Update `keepalive.ps1`** to wire up the feature to the CLI and handle side effects.
3. **Add or update Pester tests** in `KeepAlive.Tests.ps1` to cover the new feature.
4. **Update `README.md`** to document the new feature, flags, and usage.

**Example:**
```powershell
# KeepAlive.Core.ps1
function Get-KeepAliveInterval { ... }

# keepalive.ps1
param([int]$Interval)
. ./KeepAlive.Core.ps1
Start-KeepAlive -Interval $Interval

# KeepAlive.Tests.ps1
Describe "Get-KeepAliveInterval" {
  It "returns default interval" { ... }
}

# README.md
## New Feature: Custom Interval
Use `--interval` to specify the keep-alive interval.
```

---

### CI Pipeline Update or Rule Tuning

**Trigger:** When modifying CI jobs or analyzer rules for code quality  
**Command:** `/ci-tune`

1. **Edit `.github/workflows/tests.yml`** to add, modify, or fix CI steps for running tests or static analysis.
2. **Edit `PSScriptAnalyzerSettings.psd1`** to add, exclude, or whitelist rules as needed.
3. **Optionally update code files** (e.g., `keepalive.ps1`, `KeepAlive.Core.ps1`) to comply with or suppress analyzer findings.

**Example:**
```yaml
# .github/workflows/tests.yml
- name: Run Pester Tests
  run: pwsh -File ./KeepAlive.Tests.ps1

# PSScriptAnalyzerSettings.psd1
@{
  Rules = @{
    IncludeRules = @('PSAvoidUsingWriteHost')
    ExcludeRules = @('PSUseSingularNouns')
  }
}
```

---

### Fix Analyzer or Locale Issue

**Trigger:** When CI or code review surfaces analyzer warnings/errors or locale-related bugs  
**Command:** `/fix-analyzer`

1. **Edit code files** (`keepalive.ps1`, `KeepAlive.Core.ps1`) to fix the flagged issue (e.g., inline constants, locale-safe matching, variable scope).
2. **Optionally update `PSScriptAnalyzerSettings.psd1`** to suppress or exclude the rule if the pattern is intentional.
3. **Optionally update `.github/workflows/tests.yml`** if CI logic needs to be adjusted.

**Example:**
```powershell
# keepalive.ps1
# Fix: Use culture-invariant string comparison
if ($input -eq $expected -CultureInvariant) { ... }

# PSScriptAnalyzerSettings.psd1
@{
  Rules = @{
    ExcludeRules = @('PSAvoidUsingWriteHost')
  }
}
```

---

## Testing Patterns

- **Testing framework:** Unknown (likely Pester for PowerShell scripts)
- **Test file pattern:** `*.test.*` (e.g., `KeepAlive.Tests.ps1`)
- **Tests are located in dedicated files** and cover both core logic and CLI integration.
- **Example test:**
  ```powershell
  Describe "KeepAlive.Core" {
    It "returns correct interval for default" {
      (Get-KeepAliveInterval) | Should -Be 60
    }
  }
  ```

---

## Commands

| Command        | Purpose                                                        |
|----------------|----------------------------------------------------------------|
| /new-feature   | Start the workflow for adding a new feature with tests & docs  |
| /ci-tune       | Tune CI pipeline or static analyzer rules                      |
| /fix-analyzer  | Fix code for analyzer or locale issues after CI/code review    |
```
