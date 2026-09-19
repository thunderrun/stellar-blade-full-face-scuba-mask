# UE 4.26 build recipe

This recipe was tested with Unreal Engine **4.26.2** on Windows. It imports the supplied FBX into an isolated project and cooks the custom accessory chunk. It does not install files or start the game.

Install UE 4.26.2 yourself. From the repository directory, set local paths and run the phases in order:

```powershell
$env:UE426_ROOT = 'D:\Engines\UE_4.26'
$env:STELLAR_BLADE_PAKS = 'D:\SteamLibrary\steamapps\common\StellarBlade\SB\Content\Paks'
.\ue\Build-ScubaMask.ps1 -Phase Validate
.\ue\Build-ScubaMask.ps1 -Phase Import
.\ue\Build-ScubaMask.ps1 -Phase Package
```

Replace the example paths with your own. `-EngineRoot` and `-GamePaks` arguments can be used instead of environment variables. The game folder is read only. The collision check is a filename heuristic for names such as `pakchunk947` and can miss renamed containers, including `CodexCNS-ScubaMask-947`. Inspect actual container IDs before distribution or replacement; choose an unused chunk ID in `manifest.json` when needed. Do not delete unrelated mods.

The import phase creates one skeletal mesh and nine material instances under `/Game/OutfitMods/CodexScubaMask`. It verifies exact float32 scalar values, source material order, one `Root` bone and the expected skeleton reference. The source FBX hash is recorded so changed exports cannot be packaged using a stale import report.

The game supplies these external dependencies at runtime:

- `ACC_GLA_03M_Skeleton`, the glasses accessory's single-Root skeleton.
- `MI_ACC_GLA_01` and `MI_ACC_Glass_Base`, existing material parents.
- The game's flat normal texture and the engine's white texture.

The scripts generate dummy local assets only to maintain those references during cooking. The dummy content belongs to chunk 0 and **must not be distributed**. Do not upload the complete archive or generated `Content` folder.

The Package phase copies only the selected custom `.pak`, `.utoc` and `.ucas` triple to `ue/Build/SelectedChunk/`. Before distribution, inspect the selected container's asset list and re-export the cooked mesh to verify the skeleton, nine material sections, positions, weights and material references. The generated package report intentionally does not label an uninspected build release-ready.

After verifying the build, bundle those three files with `cns/CodexCNS-ScubaMask.dekcns.json` from the repository root. Those are the four files installed into CNS's `Cosmetics/CodexScubaMask/` directory as described in the main README. Keep the three container files' basenames matching one another. The build script does not install files or alter your CNS configuration.

Generated `Build`, `Saved`, logs, dummy content and local reports are ignored by Git. They can contain local paths. `References/material-parameter-contract.json` is a small interoperability contract of parameter names/defaults and external asset identifiers, not a copy of game shader graphs or textures.
