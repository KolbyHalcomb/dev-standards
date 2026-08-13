<#
.SYNOPSIS
    Link this plugin's skills into Codex's user-scope skills directory.

.DESCRIPTION
    Codex resolves user-scope skills from $HOME/.agents/skills, where **each
    subdirectory is one skill** containing SKILL.md. The plugin stores them at
    plugins/<plugin>/skills/<skill>/SKILL.md, so the two layouts differ by one
    level: a single junction of the whole skills/ folder would produce
    ~/.agents/skills/<plugin>/<skill>/SKILL.md and Codex would find no SKILL.md
    at the level it looks. The skills would silently not exist.

    So this creates one junction per skill instead.

    Directory junctions are used rather than git symlinks on purpose. Git stores
    a symlink correctly as mode 120000, but a Windows checkout with
    core.symlinks=false materializes it as a small text file containing the
    target path -- valid in the index, inert in the working tree. Junctions are
    created locally, need no administrator rights, and are unaffected by that
    setting.

    Idempotent: re-run after adding or removing a skill. Existing junctions are
    refreshed and ones whose skill no longer exists are removed.

.PARAMETER PluginName
    Plugin under plugins/ to link. Defaults to kolby-workflow.

.PARAMETER SkillsRoot
    Codex user-scope skills directory. Defaults to $HOME/.agents/skills.

.PARAMETER WhatIf
    Show what would change without touching anything.

.EXAMPLE
    pwsh -File scripts/sync-codex-skills.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$PluginName = 'kolby-workflow',
    [string]$SkillsRoot = (Join-Path $HOME '.agents\skills')
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$pluginSkills = Join-Path $repoRoot "plugins\$PluginName\skills"

if (-not (Test-Path -LiteralPath $pluginSkills)) {
    throw "No skills directory at $pluginSkills. Is -PluginName correct?"
}

# A junction is a directory reparse point. Testing the attribute matters: it is
# what keeps the cleanup below from ever recursing into a real directory.
function Test-IsJunction {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

# Delete the reparse point itself, never its contents. Remove-Item -Recurse on a
# junction has historically followed the link on Windows PowerShell, which would
# delete the source skills out of the repo.
function Remove-Junction {
    param([string]$Path)
    [System.IO.Directory]::Delete($Path, $false)
}

if (-not (Test-Path -LiteralPath $SkillsRoot)) {
    if ($PSCmdlet.ShouldProcess($SkillsRoot, 'Create skills directory')) {
        New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null
        Write-Host "Created $SkillsRoot"
    }
} elseif (Test-IsJunction -Path $SkillsRoot) {
    # An earlier attempt may have junctioned the whole folder. That layout hides
    # SKILL.md one level too deep, and it also means anything else installed at
    # user scope would land inside this repo.
    throw "$SkillsRoot is itself a junction. Remove it (rmdir, which deletes only the link) and re-run so each skill can be linked individually."
}

$sourceSkills = Get-ChildItem -LiteralPath $pluginSkills -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') }

if (-not $sourceSkills) {
    throw "Found no skills under $pluginSkills. A sync that links nothing is a broken sync, not a clean run."
}

$expected = @{}
foreach ($skill in $sourceSkills) { $expected[$skill.Name] = $skill.FullName }

$linked = 0
foreach ($name in $expected.Keys | Sort-Object) {
    $target = $expected[$name]
    $link = Join-Path $SkillsRoot $name

    if (Test-IsJunction -Path $link) {
        $current = (Get-Item -LiteralPath $link -Force).Target | Select-Object -First 1
        if ($current -eq $target) {
            Write-Host "  ok       $name"
            $linked++
            continue
        }
        if ($PSCmdlet.ShouldProcess($link, 'Repoint junction')) { Remove-Junction -Path $link }
    } elseif (Test-Path -LiteralPath $link) {
        Write-Warning "  skipped  $name -- a real directory or file is already there; not touching it"
        continue
    }

    if ($PSCmdlet.ShouldProcess($link, "Junction -> $target")) {
        New-Item -ItemType Junction -Path $link -Target $target | Out-Null
        Write-Host "  linked   $name"
        $linked++
    }
}

# Remove junctions for skills that no longer exist. Only reparse points are
# considered, so a real directory someone put here is never touched.
# Guarded: under -WhatIf the root above was not actually created, and there is
# nothing to clean up on a first run either way.
foreach ($item in @(if (Test-Path -LiteralPath $SkillsRoot) {
            Get-ChildItem -LiteralPath $SkillsRoot -Directory -Force
        })) {
    if ($expected.ContainsKey($item.Name)) { continue }
    if (-not (Test-IsJunction -Path $item.FullName)) { continue }
    $itemTarget = (Get-Item -LiteralPath $item.FullName -Force).Target | Select-Object -First 1
    if ($itemTarget -notlike "$pluginSkills*") { continue }
    if ($PSCmdlet.ShouldProcess($item.FullName, 'Remove stale junction')) {
        Remove-Junction -Path $item.FullName
        Write-Host "  removed  $($item.Name) (no longer in the plugin)"
    }
}

Write-Host ""
Write-Host "$linked skill(s) available to Codex from $SkillsRoot"
