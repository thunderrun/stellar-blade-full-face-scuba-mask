[CmdletBinding()]
param(
    [string]$GameRoot = 'C:\Program Files (x86)\Steam\steamapps\common\StellarBlade',
    [switch]$CheckOnly,
    [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'
$packageRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$gameDirectory = [IO.Path]::GetFullPath($GameRoot)
$manifest = Get-Content -LiteralPath (Join-Path $packageRoot 'package-manifest.json') -Raw | ConvertFrom-Json
$relativeAudio = 'SB/Content/Paks/~mods/CodexRunningBreath'
$relativeLua = 'SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath'
$scopes = @([IO.Path]::GetFullPath((Join-Path $gameDirectory $relativeAudio)),
            [IO.Path]::GetFullPath((Join-Path $gameDirectory $relativeLua)))
$expected = @(
    "$relativeAudio/Codex-RunningBreath-19530.pak",
    "$relativeAudio/Codex-RunningBreath-19530.ucas",
    "$relativeAudio/Codex-RunningBreath-19530.utoc",
    "$relativeLua/Scripts/main.lua",
    "$relativeLua/Scripts/config.lua",
    "$relativeLua/Scripts/running_state.lua",
    "$relativeLua/enabled.txt"
)
if ($manifest.name -cne 'CodexRunningBreath' -or $manifest.version -cne '0.2.9' -or
    @($manifest.files).Count -ne 7 -or @(Compare-Object $expected @($manifest.files.relative_path) -CaseSensitive).Count) {
    throw 'Unexpected package identity or file allowlist.'
}
function Assert-Closed {
    $active = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.Name -in @('SB.exe','SB-Win64-Shipping.exe','StellarBlade.exe')
    })
    if ($active.Count) { throw 'Save and close Stellar Blade before installing or removing this add-on.' }
}
function Target-Path([string]$relative) {
    $path = [IO.Path]::GetFullPath((Join-Path $gameDirectory $relative))
    if (-not @($scopes | Where-Object { $path.StartsWith($_ + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) }).Count) {
        throw 'File path escaped the two add-on folders.'
    }
    return $path
}
function Assert-Hash([string]$path, $row) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw ('Missing package file: ' + $path) }
    $item = Get-Item -LiteralPath $path
    $hasher = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($path)
    try { $digest = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -ne $row.bytes -or
        $digest -cne $row.sha256) {
        throw ('Package file changed: ' + $path)
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $gameDirectory 'SB/Content/Paks') -PathType Container) -or
    -not (Test-Path -LiteralPath (Join-Path $gameDirectory 'SB/Binaries/Win64/ue4ss/UE4SS.dll') -PathType Leaf)) {
    throw 'Select the StellarBlade game folder with working UE4SS installed.'
}
foreach ($row in $manifest.files) {
    $source = [IO.Path]::GetFullPath((Join-Path $packageRoot $row.relative_path))
    if (-not $source.StartsWith($packageRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source path escaped package.' }
    Assert-Hash $source $row
    $null = Target-Path $row.relative_path
}
foreach ($scope in $scopes) {
    if (Test-Path -LiteralPath $scope) {
        if ((Get-Item -LiteralPath $scope).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Add-on folder is a filesystem link.' }
    }
}
if ($Uninstall) {
    $found = @($scopes | Where-Object { Test-Path -LiteralPath $_ })
    if (-not $found.Count) { Write-Output 'This add-on is not installed.'; return }
    $targetFiles = @($manifest.files | ForEach-Object { Target-Path $_.relative_path })
    $present = @($found | ForEach-Object { Get-ChildItem -LiteralPath $_ -File -Recurse })
    if (@($present | Where-Object { $_.FullName -notin $targetFiles }).Count -or $present.Count -ne 7) {
        throw 'Add-on folders contain unexpected or missing files; nothing removed.'
    }
    foreach ($row in $manifest.files) { Assert-Hash (Target-Path $row.relative_path) $row }
    if ($CheckOnly) { Write-Output 'Uninstall checks passed; no files changed.'; return }
    Assert-Closed
    foreach ($row in $manifest.files) {
        Assert-Closed
        $target = Target-Path $row.relative_path
        Assert-Hash $target $row
        Remove-Item -LiteralPath $target
    }
    # Only known, now-empty directories. No recursive removal.
    foreach ($directory in @((Join-Path $scopes[1] 'Scripts'),$scopes[1],$scopes[0])) {
        if ((Test-Path -LiteralPath $directory) -and -not @(Get-ChildItem -LiteralPath $directory -Force).Count) {
            Remove-Item -LiteralPath $directory
        }
    }
    Write-Output 'Removed only CodexRunningBreath.'
    return
}
foreach ($scope in $scopes) {
    if (Test-Path -LiteralPath $scope) { throw 'Add-on folder already exists; it will not be overwritten. Remove the prior add-on first.' }
}
$paks = Join-Path $gameDirectory 'SB/Content/Paks'
foreach ($utoc in Get-ChildItem -LiteralPath $paks -Filter '*.utoc' -File -Recurse) {
    $bytes = [IO.File]::ReadAllBytes($utoc.FullName)
    if ($bytes.Length -lt 64 -or [Text.Encoding]::ASCII.GetString($bytes,0,16) -cne '-==--==--==--==-') {
        throw ('Could not check native container identity: ' + $utoc.FullName)
    }
    if ([BitConverter]::ToUInt64($bytes,56).ToString('x16') -ceq $manifest.container_id) {
        throw ('Audio container ID already exists: ' + $utoc.FullName)
    }
}
if ($CheckOnly) { Write-Output 'Package, target and container checks passed; no files changed.'; return }
Assert-Closed
$created = @()
$temps = @()
try {
    foreach ($row in $manifest.files) {
        Assert-Closed
        $target = Target-Path $row.relative_path
        $temp = $target + '.running-breath-install.tmp'
        if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $temp)) { throw 'A target appeared during installation.' }
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        $temps += $temp
        Copy-Item -LiteralPath (Join-Path $packageRoot $row.relative_path) -Destination $temp
        Assert-Hash $temp $row
        Assert-Closed
        Move-Item -LiteralPath $temp -Destination $target
        $created += $row
    }
    foreach ($row in $manifest.files) { Assert-Hash (Target-Path $row.relative_path) $row }
} catch {
    $errorRecord = $_
    Assert-Closed
    foreach ($row in $created) {
        $target = Target-Path $row.relative_path
        Assert-Hash $target $row
        Remove-Item -LiteralPath $target
    }
    foreach ($temp in $temps) {
        if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp }
    }
    throw $errorRecord
}
Write-Output 'Installed CodexRunningBreath 0.2.9. #2 idle after movement only; #3 running and louder sprint.'
