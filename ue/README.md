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

The import phase creates one skeletal mesh and **12 material instances** under `/Game/OutfitMods/CodexScubaMask`. It verifies exact float32 scalar values, source material order, one `Root` bone and the expected skeleton reference. The source FBX hash is recorded so changed exports cannot be packaged using a stale import report.

Version **1.1.9** adds **49,404 hood triangles** in section **11**, `M_Scuba_LatexHood`, for **97,798 total triangles and 12 material slots**. The existing **48,394 mask triangles in sections 0–10** retain their coordinates, corner normals, UVs, material definitions and Root weights. The broad lower cup and direct collar remain in section **7** (16,948 triangles), and the complete visor remains in section **8** (11,450 triangles). With Hood Off, Cup Off leaves 31,446 exterior mask triangles. The hood is a thin closed glossy black latex shell covering the scalp, ears, sides, back and under-chin area, with a face opening beneath the mask and a short neck cuff. Hair is untouched.

Version 1.1.9 includes the visible **Hood** CNS On/Off control for section **11**, default **Off**. The existing **Valve** control still hides sections **1, 4, 9 and 10** together through `ControlledBy` and defaults to **On**. Turning Valve Off leaves the existing cup collar and visor valve opening. The hood requires a fresh FBX export followed by **Import** and **Package**, and installation of all three rebuilt archives plus the new JSON. A JSON-only update cannot add its mesh and material. The complete package is linked from the [1.1.9 GitHub release](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/releases/tag/v1.1.9).

The existing 1.1.7 `UserConfigs.VectorControls` for **Glass Color** (slot 8) and **Inner Cup Color** (slot 7) remain unchanged. Each visible `GlassColor Out` control has a hidden `GlassColor In` partner linked through `ControlledBy`. Use `Association: Global`, `LayerIndex: -1`, `Sliders: [true, true, true, false]`, RGB range 0-1 and alpha 1. Defaults match the cooked materials: glass `[0.12, 0.12, 0.12, 1]`, cup `[0.18, 0.18, 0.18, 1]`. The older `OutfitDatas` preset vectors are removed to avoid competing color writers; the original single mesh path and item ID are retained. The **Inner Nasal Cup** toggle and scalar opacity rows remain unchanged, with cup default On, visor opacity 0.10 and cup opacity 0.20.

Version 1.1.0 keeps the original geometry and material values. It moves 1,212 lower exterior faceplate triangles into visor section 8. The CNS configuration hides only cup section 7, so the complete outer shell remains visible. Preserve the zero-based material order during editing/import.

The game supplies these external dependencies at runtime:

- `ACC_GLA_03M_Skeleton`, the glasses accessory's single-Root skeleton.
- `MI_ACC_GLA_01` and `MI_ACC_Glass_Base`, existing material parents.
- The game's flat normal texture and the engine's white texture.

The scripts generate dummy local assets only to maintain those references during cooking. The dummy content belongs to chunk 0 and **must not be distributed**. Do not upload the complete archive or generated `Content` folder.

The Package phase copies only the selected custom `.pak`, `.utoc` and `.ucas` triple to `ue/Build/SelectedChunk/`. Before distribution, inspect the selected container's asset list and re-export the cooked mesh to verify the skeleton, **12 material sections**, positions, weights and material references. Cup section 7 must contain 16,948 triangles, visor section 8 must contain 11,450, and hood section 11 must contain **49,404**, with **97,798 total**. Hiding section 11 must leave the original 48,394-triangle mask exactly intact; hiding section 7 must leave the lower faceplate and a closed outer visor. Valve sections 1, 4, 9 and 10 must contain only the exterior valve assembly, with the non-valve vent/accent geometry preserved in its original sections. The generated package report intentionally does not label an uninspected build release-ready.

After verifying the build, bundle those three files with `cns/CodexCNS-ScubaMask.dekcns.json` from the repository root. Those are the four files installed into CNS's `Cosmetics/CodexScubaMask/` directory as described in the main README. Keep the three container files' basenames matching one another. The build script does not install files or alter your CNS configuration.

Generated `Build`, `Saved`, logs, dummy content and local reports are ignored by Git. They can contain local paths. `References/material-parameter-contract.json` is a small interoperability contract of parameter names/defaults and external asset identifiers, not a copy of game shader graphs or textures.

The retained 1.1.6 and 1.1.8 reports are tied to their historical source/export/build hashes. The final 1.1.9 source passed independent checks for exact preservation of mask sections 0–10 and the Root rig, closed manifold topology, consistent winding, and no detected skin or self-intersections. It matches the approved candidate whose neutral fitting and coverage were inspected in glossy and matte Blender views. Source/export validation passed for all 97,798 triangles, 12 material slots, FBX roundtrip and rigid Root weights. Native container integrity, cooked geometry/connectivity and skeleton/material-reference checks passed. The installation receipt records matching payload hashes and unchanged saved settings at installation.

Live checks in **Stellar Blade 2.1 with CNS 2.2** passed independent Cup/Valve/Hood On/Off, visor opacity **0.10 → 0.99 → 0.10**, independent cyan visor/yellow cup presets, normal rendering, and crown/ear/side/rear hood coverage. Hair was temporarily hidden through CNS for the coverage screenshots; this mod neither changes nor hides hair. A full game close and relaunch, then loading the existing camp save, preserved **Hood On, Valve Off, Cup Off, cyan visor, black cup, visor opacity 0.10 and cup opacity 0.20**. See [runtime validation](../assets/runtime_validation.json).

The live inspection was limited to camp/idle and restart persistence; broad combat movement and extreme poses remain untested. The hood shares the rigid glasses Root attachment: its short neck cuff does not deform with neck motion or facial expressions.
