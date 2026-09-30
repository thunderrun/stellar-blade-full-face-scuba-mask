# Audio asset source project

This is an isolated Unreal Engine **4.26** content project named `SB`. Keep that
project name and the `/Game/CodexRunningBreath/Audio` asset paths: the game and
runtime script expect them. The project enables PythonScriptPlugin and
EditorScriptingUtilities for the editor.

The two prepared PCM WAVs live one directory above this project, under
`source/audio/`. Verify them with `python prepare_dual_audio.py` from the optional
component directory. To prepare your own original 16-bit PCM recordings instead,
use `--run <recording-3.wav> --walk <recording-2.wav>`; processing requires NumPy
and writes separate loop files without modifying the inputs.

Import using UE4.26's Python commandlet. For example, in PowerShell from the
optional component directory, set `$editor` to your `UE4Editor-Cmd.exe` path:

```powershell
$project = (Resolve-Path .\ue\SB.uproject).Path
$script = (Resolve-Path .\ue\Content\Python\import_dual_audio.py).Path
& $editor $project -run=pythonscript "-script=$script" -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput
```

This commandlet form was used for the local audio import. The script creates
`SW_RunBreathingLoop` and `SW_WalkBreathingLoop`, enables looping and
`PLAY_WHEN_SILENT` virtualization, disables streaming, and saves an import report
under `Saved/`. Generated editor assets and reports are not source-control inputs.

Full container rebuilding needs additional work beyond import. Cook for
`WindowsNoEditor`, then select only these two cooked audio packages and their
required companions into an isolated native UE4.26 IoStore container with an
empty companion `.pak`. The local release used native UE4.26 container generation
and chunk SHA1 verification; it did not use a generic retoc repack. No tested,
portable end-to-end cook/container script is included here. The package helper
can reuse the already audited audio from an existing release instead. Do not
deploy editor `.uasset` files, generated global containers, or the entire cook.

The optional C# auditor requires a .NET 10 SDK, its pinned NuGet dependencies,
the installed game's `SB/Content/Paks` (including `global.utoc`), and a matching
`.usmap`. Supply those paths explicitly; an Oodle library is optional unless the
input metadata requires it. These external game/tool files are not redistributed.
The preparation report must be beside the output audit JSON:

```text
dotnet run --project audit/Audit.csproj -- <selected-container-dir> checks/cooked-audio-audit.json --game-paks <game-Paks-dir> --usmap <mapping.usmap> [--oodle <library-path>]
```

The same paths may be supplied through `SB_GAME_PAKS`, `SB_USMAP`, and
`SB_OODLE_DLL`. The auditor checks the selected custom packages and installed
container-ID collisions; it does not prove in-game playback. Generated logs,
audits, `Saved`, `Intermediate`, and `DerivedDataCache` remain local build output.
