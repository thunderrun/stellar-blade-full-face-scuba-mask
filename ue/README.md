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

Geometry version 1.1.6 replaces the exposed vertical pipe with a broad lower cup and short direct valve collar (section 7, 16,948 triangles). Opaque sections 0-6 and all 39 under-chin seal points are exact; visor section 8 changes only around the concealed enlarged valve aperture (11,450 triangles). All material definitions are preserved. Total geometry is 48,394 triangles; Cup Off leaves 31,446 exterior triangles. Rebuilding this geometry requires Import and Package; the 1.1.7 color-settings update reuses these archives without a recook.

Configuration version 1.1.7 exposes `UserConfigs.VectorControls` for **Glass Color** (slot 8) and **Inner Cup Color** (slot 7). Each visible `GlassColor Out` control has a hidden `GlassColor In` partner linked through `ControlledBy`. Use `Association: Global`, `LayerIndex: -1`, `Sliders: [true, true, true, false]`, RGB range 0-1 and alpha 1. Defaults match the cooked materials: glass `[0.12, 0.12, 0.12, 1]`, cup `[0.18, 0.18, 0.18, 1]`. The older `OutfitDatas` preset vectors are removed to avoid competing color writers; the original single mesh path and item ID are retained. Opacity remains controlled by the unchanged scalar rows.

Version 1.1.0 keeps the original geometry and material values. It moves 1,212 lower exterior faceplate triangles into visor section 8. The CNS configuration hides only cup section 7, so the complete outer shell remains visible. Preserve the zero-based material order during editing/import.

The game supplies these external dependencies at runtime:

- `ACC_GLA_03M_Skeleton`, the glasses accessory's single-Root skeleton.
- `MI_ACC_GLA_01` and `MI_ACC_Glass_Base`, existing material parents.
- The game's flat normal texture and the engine's white texture.

The scripts generate dummy local assets only to maintain those references during cooking. The dummy content belongs to chunk 0 and **must not be distributed**. Do not upload the complete archive or generated `Content` folder.

The Package phase copies only the selected custom `.pak`, `.utoc` and `.ucas` triple to `ue/Build/SelectedChunk/`. Before distribution, inspect the selected container's asset list and re-export the cooked mesh to verify the skeleton, nine material sections, positions, weights and material references. In particular, cup section 7 must contain 16,948 triangles and visor section 8 must contain 11,450, with 48,394 total. Hiding section 7 must leave the lower faceplate and a closed outer visor. The generated package report intentionally does not label an uninspected build release-ready.

After verifying the build, bundle those three files with `cns/CodexCNS-ScubaMask.dekcns.json` from the repository root. Those are the four files installed into CNS's `Cosmetics/CodexScubaMask/` directory as described in the main README. Keep the three container files' basenames matching one another. The build script does not install files or alter your CNS configuration.

Generated `Build`, `Saved`, logs, dummy content and local reports are ignored by Git. They can contain local paths. `References/material-parameter-contract.json` is a small interoperability contract of parameter names/defaults and external asset identifiers, not a copy of game shader graphs or textures.
