[CmdletBinding()]
param(
    [ValidateSet('Validate', 'Import', 'Package')]
    [string]$Phase = 'Validate',
    [string]$EngineRoot = $env:UE426_ROOT,
    [string]$GamePaks = $env:STELLAR_BLADE_PAKS
)

$ErrorActionPreference = 'Stop'
if (-not $EngineRoot) { throw 'Set UE426_ROOT or pass -EngineRoot for Unreal Engine 4.26.2.' }
if (-not $GamePaks) { throw 'Set STELLAR_BLADE_PAKS or pass -GamePaks for the game Paks folder.' }
Import-Module Microsoft.PowerShell.Utility
$projectRoot = $PSScriptRoot
$projectFile = Join-Path $projectRoot 'SB.uproject'
$manifestPath = Join-Path $projectRoot 'manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$fbxPath = [IO.Path]::GetFullPath((Join-Path $projectRoot $manifest.fbx))
$editor = Join-Path $EngineRoot 'Engine\Binaries\Win64\UE4Editor-Cmd.exe'
$uat = Join-Path $EngineRoot 'Engine\Build\BatchFiles\RunUAT.bat'
$versionFile = Join-Path $EngineRoot 'Engine\Build\Build.version'
$reportFile = Join-Path $projectRoot 'Saved\scuba-import-report.json'
$archiveRoot = Join-Path $projectRoot ('Build\Archive\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$selectedRoot = Join-Path $projectRoot 'Build\SelectedChunk'
$chunkId = [int]$manifest.chunk_id

if ($chunkId -le 0) { throw 'The mod chunk ID must be positive.' }
if (@($manifest.expected_bones).Count -ne 1 -or $manifest.expected_bones[0] -cne 'Root') {
    throw 'This project requires exactly the vanilla glasses Root bone.'
}
if (@($manifest.materials).Count -ne [int]$manifest.expected_material_count) { throw 'Material definitions differ from the revision manifest count.' }
if (-not (Test-Path -LiteralPath $GamePaks -PathType Container)) { throw "Game Paks folder not found: $GamePaks" }
# Read-only collision check over base and installed mod containers, including custom names.
$collisionPattern = '(?i)(?:pak)?chunk' + $chunkId + '(?:[-_.]|$)'
$collisions = @(Get-ChildItem -LiteralPath $GamePaks -Recurse -File |
    Where-Object { $_.Extension -in @('.pak', '.utoc', '.ucas') -and $_.BaseName -match $collisionPattern })
if ($collisions.Count -gt 0) { throw ('Chunk ID filename collision: ' + ($collisions.FullName -join ', ')) }
$check = [ordered]@{
    phase = $Phase
    fbx = $fbxPath
    fbx_present = (Test-Path -LiteralPath $fbxPath -PathType Leaf)
    ue_editor_present = (Test-Path -LiteralPath $editor -PathType Leaf)
    ue_uat_present = (Test-Path -LiteralPath $uat -PathType Leaf)
    chunk_id = $chunkId
    installed_filename_collisions = $collisions.Count
    original_skeleton = $manifest.original_skeleton
    note = 'Filename collision check is not a container-ID audit. Re-export and inspect the cooked chunk before installation.'
}
if (Test-Path -LiteralPath $versionFile -PathType Leaf) {
    $engineVersion = Get-Content -LiteralPath $versionFile -Raw | ConvertFrom-Json
    $check.engine_version = '{0}.{1}.{2}' -f $engineVersion.MajorVersion, $engineVersion.MinorVersion, $engineVersion.PatchVersion
    if ($engineVersion.MajorVersion -ne 4 -or $engineVersion.MinorVersion -ne 26) { throw 'Only Unreal Engine 4.26 is supported.' }
}
$check | ConvertTo-Json -Depth 5
if ($Phase -eq 'Validate') { return }
if (-not $check.fbx_present) { throw 'The fitted FBX must be exported before importing.' }
if (-not $check.ue_editor_present -or -not $check.ue_uat_present) { throw 'Install Unreal Engine 4.26 before running Import or Package.' }

if ($Phase -eq 'Import') {
    # Stale success reports cannot be mistaken for a successful new import.
    if (Test-Path -LiteralPath $reportFile) {
        $previousReport = Join-Path $projectRoot ('Saved\scuba-import-report.previous-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.json')
        Move-Item -LiteralPath $reportFile -Destination $previousReport
    }
    $scriptPath = Join-Path $projectRoot 'Content\Python\import_scuba_mask.py'
    $importLog = Join-Path $projectRoot 'Saved\Logs\ScubaImport.log'
    & $editor $projectFile '-run=pythonscript' "-script=$scriptPath" "-abslog=$importLog" '-unattended' '-nop4' '-nosplash' '-stdout' '-FullStdOutLogOutput'
    if ($LASTEXITCODE -ne 0) { throw "UE import failed with exit code $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $reportFile)) { throw 'UE import produced no verification report.' }
    $report = Get-Content -LiteralPath $reportFile -Raw | ConvertFrom-Json
    if (-not $report.success) { throw ('UE import failed: ' + $report.error) }
    $report | ConvertTo-Json -Depth 10
    return
}

if (-not (Test-Path -LiteralPath $reportFile)) { throw 'Run the Import phase successfully first.' }
$report = Get-Content -LiteralPath $reportFile -Raw | ConvertFrom-Json
if (-not $report.success) { throw 'Last UE import did not succeed.' }
if ($report.fbx_sha256 -ne (Get-FileHash -LiteralPath $fbxPath -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'FBX changed after import. Run Import again before Package.'
}
if ($report.manifest_sha256 -ne (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'Manifest changed after import. Run Import again before Package.'
}
if ($report.source_manifest_sha256 -ne (Get-FileHash -LiteralPath $report.source_manifest -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'Blender export manifest changed after import. Run Import again before Package.'
}
if ($report.material_reference_sha256 -ne (Get-FileHash -LiteralPath $report.material_reference -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'Verified game-material reference changed after import. Run Import again before Package.'
}
if ($report.skeleton -cne $manifest.original_skeleton -or [int]$report.chunk_id -ne $chunkId) {
    throw 'The import report does not match the current manifest.'
}
New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
& $uat 'BuildCookRun' "-project=$projectFile" '-noP4' '-clientconfig=Shipping' '-serverconfig=Shipping' '-nocompile' '-nocompileeditor' '-installed' '-targetplatform=Win64' '-cook' '-stage' '-package' '-pak' '-iostore' '-archive' "-archivedirectory=$archiveRoot" '-utf8output' '-unattended'
if ($LASTEXITCODE -ne 0) { throw "UE package failed with exit code $LASTEXITCODE" }
$chunkPattern = '^pakchunk' + $chunkId + '-WindowsNoEditor(?:_P)?$'
$files = @(Get-ChildItem -LiteralPath $archiveRoot -Recurse -File | Where-Object {
    $_.BaseName -match $chunkPattern -and $_.Extension -in @('.pak', '.utoc', '.ucas')
})
if ($files.Count -ne 3 -or @($files.Extension | Sort-Object -Unique).Count -ne 3) {
    throw 'Expected one custom chunk .pak/.utoc/.ucas triple. Inspect the archive before continuing.'
}
New-Item -ItemType Directory -Path $selectedRoot -Force | Out-Null
foreach ($file in $files) { Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $selectedRoot $file.Name) -Force }
$packageReport = [ordered]@{
    build_completed = $true
    release_ready = $false
    expected_custom_assets = $report.explicit_custom_assets
    excluded_skeleton = $manifest.original_skeleton
    files = @($files | ForEach-Object {
        $copy = Join-Path $selectedRoot $_.Name
        @{path = $copy; bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash}
    })
    required_next_step = 'Read-only archive listing plus cooked mesh re-export: verify only intended assets, one Root bone and its reference quaternion, fitted vertex bounds, material slots, and original skeleton reference. Then verify in game through CNS.'
}
$packageReport | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $projectRoot 'Build\package-report.json') -Encoding UTF8
$packageReport | ConvertTo-Json -Depth 10
