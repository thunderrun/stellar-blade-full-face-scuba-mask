# UE 4.26 build recipe

This recipe uses Unreal Engine **4.26.2** on Windows. It imports the supplied FBX files into an isolated project and cooks the custom accessory chunk. It does not install files or start the game.

Install UE 4.26.2 yourself. From the repository directory, set local paths and run the phases in order:

```powershell
$env:UE426_ROOT = 'D:\Engines\UE_4.26'
$env:STELLAR_BLADE_PAKS = 'D:\SteamLibrary\steamapps\common\StellarBlade\SB\Content\Paks'
.\ue\Build-ScubaMask.ps1 -Phase Validate
.\ue\Build-ScubaMask.ps1 -Phase Import
.\ue\Build-ScubaMask.ps1 -Phase Package
```

Replace the example paths with your own. `-EngineRoot` and `-GamePaks` arguments can be used instead of environment variables. The game folder is read only. The chunk-collision check is a filename heuristic and can miss renamed containers, including `CodexCNS-ScubaMask-947`. Inspect actual container IDs before distribution or replacement; choose an unused chunk ID in `manifest.json` when needed. Do not delete unrelated mods.

Version **1.2.2, revision 18** contains two mesh variants, **Scuba cup** (`SK_CodexScubaMask`, **97,798 triangles**) and **Large oral-nasal cup** (`SK_CodexGasMask`, **127,646 triangles**), each with **12 material slots**. Hood section 11 fits closer around the temples, ears, scalp and back, with a smoother lower-side transition into the short cuff. Filter sections 12–13 and the Side Filters CNS option are removed. All mask sections 0–10 retain their 1.2.1 geometry, including both cups, the fixed collar and through-bore. The large cup still contains **46,796 triangles**: 40,396 for the smoothed body and 6,400 for its two inlet-valve assemblies. The variants differ only in cup section 7.

The import creates both skeletal meshes and **12 shared material instances** under `/Game/OutfitMods/CodexScubaMask`, for **14 custom asset packages** in the selected chunk. It checks exact float32 scalar values, source material order, one `Root` bone and the expected skeleton reference. Source FBX hashes are recorded to prevent packaging stale imports after an export changes.

| Section | Expected content | Scuba cup triangles | Large cup triangles |
| --- | --- | --- | --- |
| 0–10 | Mask and selected cup | 48,394 | 78,242 |
| 7, included above | Cup, seal and collar; large cup includes inlet valves | 16,948 | 46,796 |
| 8, included above | Complete visor/lower faceplate | 11,450 | 11,450 |
| 1, 4, 9, 10, included above | Exterior chin valve only | 5,066 | 5,066 |
| 11 | Latex hood | 49,404 | 49,404 |
| Total | All sections | 97,798 | 127,646 |

Preserve the zero-based material order. Both cup variants use section 7 and share the same material and rig contract. The larger cup's two inlet valves are included in its section 7 count, material and visibility. With Hood hidden, the Scuba cup mesh contains the 48,394-triangle mask; additionally hiding Cup leaves 31,446 triangles in either variant. Hood independently adds 49,404 triangles. Hiding Cup must also hide its inlet valves while leaving the lower faceplate and closed outer visor intact.

CNS uses two `OutfitPaths` with matching `OutfitNames`; variant arrows select **Scuba cup** or **Large oral-nasal cup**. The existing item ID is retained. **Inner Nasal Cup** controls section 7. **Valve** controls sections 1, 4, 9 and 10 together through `ControlledBy` and means the exterior chin valve. Both default On. Turning Valve Off leaves the cup collar and existing visor valve opening.

The two shallow inlet valves are built into the larger cup and share **Inner Nasal Cup**, Inner Cup Color and Cup Opacity. **Hood** controls section 11, default Off. It covers scalp, ears, sides, back and under-chin area, with a face opening under the mask and short neck cuff. The closer fit reduces the previous side volume without changing or hiding hair. The surviving CNS settings retain their existing IDs, defaults and links; only Side Filters is removed.

The existing `VectorControls` for **Glass Color** (slot 8) and **Inner Cup Color** (slot 7) remain. Each visible `GlassColor Out` has a hidden `GlassColor In` partner linked through `ControlledBy`. Use `Association: Global`, `LayerIndex: -1`, `Sliders: [true, true, true, false]`, RGB range 0–1 and alpha 1. Defaults match the cooked materials: glass `[0.12, 0.12, 0.12, 1]`, cup `[0.18, 0.18, 0.18, 1]`. Old color-preset `OutfitDatas` vectors remain absent. Linked scalar opacity defaults remain visor 0.10 and cup 0.20.

The game supplies these external dependencies at runtime:

- `ACC_GLA_03M_Skeleton`, the glasses accessory's single-Root skeleton.
- `MI_ACC_GLA_01` and `MI_ACC_Glass_Base`, existing material parents.
- The game's flat normal texture and the engine's white texture.

The scripts generate local placeholders only to maintain those references during cooking. Placeholder content belongs to chunk 0 and **must not be distributed**. Do not upload the complete archive or generated `Content` folder.

Package copies only the selected custom `.pak`, `.utoc` and `.ucas` triple to `ue/Build/SelectedChunk/`. Inspect the selected container's **14 custom packages** and re-export **both** cooked meshes before distribution. Verify the skeleton, all 12 sections, positions, weights and material references against each variant's source. The variants must differ only in section 7. Every mask section 0–10 must match its 1.2.1 counterpart; hood section 11 is refitted and no filter section or filter material package may remain. The generated package report does not label an uninspected build release-ready.

Bundle the three verified archives with `cns/CodexCNS-ScubaMask.dekcns.json` from the repository root. Those four files install into CNS's `Cosmetics/CodexScubaMask/` directory as described in the main README. Keep the three container basenames matching. The 1.2.2 hood fit and filter removal require rebuilt mesh archives and matching JSON: export both variants, run Import and Package, and install the full rebuilt payload. The build script does not install files or alter saved CNS configuration.

Generated Build/Saved directories, logs, placeholders and local reports are ignored by Git. They can contain local paths. `References/material-parameter-contract.json` is an interoperability contract of parameter names/defaults and external identifiers; it does not contain game shader graphs or textures.

**1.2.2 revision 18 validation:** the final hood donor passed independent closed-manifold, winding, finite-coordinate, nondegenerate-triangle and smooth-shading checks, with no detected self or neutral-skin intersections. Matched glossy and matte views show the reduced temple/ear volume and smoother lower-side transition. Median sampled nearest-skin distance decreased from approximately **3.40 to 0.81 mm at the temple**, **8.01 to 1.81 mm around the ear**, and **9.29 to 1.94 mm at the lower side**. These regional samples describe the neutral fit, not continuous global clearance or animated hair compatibility. Final source checks confirmed exact preservation of mask sections 0–10 in both variants, including the cups and inlet valves, and removal of the filter geometry, materials and control. Both exports and all 16 static visibility combinations passed. UE cooking and all seven post-build audits passed; the four locally installed files match the audited payload, and saved settings were unchanged during installation. The current source and runtime reports are `assets/tight_hood_validation.json` and `assets/tight_hood_runtime_validation.json`.

Live **1.2.2 revision 18** checks after a fresh launch in **Stellar Blade 2.1 with CNS 2.2** confirmed both named cup variants render and the Side Filters row is absent. **Hood Off/On** was checked with the current brown ponytail/bangs and **Noble Elegance**, keeping hair visible over the hood. The former broad temple bulge was reduced to a small fitted ear cover. The gas cup and its two inlet valves hide and return together through **Inner Nasal Cup**; the exterior chin **Valve** switches independently, and cup opacity works.

Closing CNS to gameplay and reopening it retained **Large oral-nasal cup**, **Cup On**, **Valve Off**, **Hood On**, **visor opacity 0.25** and **cup opacity 0.97**. Testing covered camp/idle and CNS menus. Full-game restart persistence, combat, extreme poses and all-hairstyle compatibility were not tested for 1.2.2. Hair remains unchanged; these two hairstyle checks do not guarantee clearance for every hairstyle or animated pose. After closing the game, the pre-test CNS settings were restored byte-for-byte and verified by matching SHA-256 hashes; other game save writes were preserved. See the [1.2.2 runtime report](../assets/tight_hood_runtime_validation.json).

**1.2.1 revision 17 history:** the smoothed cup passed closed-component, winding, finite-coordinate, nondegenerate-triangle and self-intersection checks, with no detected intersections against neutral skin, visor, hood or outer seal. The fixed collar region is preserved. Dense cup-body sampling measured minimum clearances of approximately **0.382 mm to skin** and **0.512 mm to visor**; these sampled distances are not continuous global minima. Independent glossy and matte front, three-quarter, profile and detail review accepted the rounder bridge and bowl, with the retained lower contact-flange transition. Final-source checks passed exact preservation of the Scuba variant, all gas-mask sections outside cup 7, materials, Root rig and CNS configuration. Both FBX/GLB exports passed and bind the integrated source hash; all 32 static toggle combinations passed. UE cooking and all seven post-build audits passed, and guarded local installation completed. Historical reports are `assets/smooth_cup_validation.json` and `assets/smooth_cup_runtime_validation.json`.

Live **1.2.1 revision 17** checks after a fresh launch in **Stellar Blade 2.1 with CNS 2.2** confirmed normal full-mask rendering and the rounded gas cup with paired inlet valves. **Scuba cup → Large oral-nasal cup → Scuba cup → Large oral-nasal cup** switching passed. **Inner Nasal Cup Off → On** hid and restored the cup and both inlets together; **Side Filters Off → On → Off → On** switched the filters independently. Hood On, cup opacity **0.20 → 0.98**, and a cyan visor with neutral then black cup color were inspected. Hair and the hairpin were temporarily hidden through CNS.

Closing and reopening CNS retained **Large oral-nasal cup**, **Cup/Valve/Hood/Side Filters all On**, **cyan glass**, **black cup**, **visor opacity 0.10** and **cup opacity 0.98**. Full-game restart persistence was **not retested for 1.2.1**. Testing covered camp/idle, with no combat or extreme-pose sweep. After closing the game, the original saved CNS settings were restored byte-for-byte and verified by matching SHA-256 hashes. See the [1.2.1 runtime report](../assets/smooth_cup_runtime_validation.json).

**1.2.0 revision 16 history:** independent source checks passed exact preservation of shared sections 0–13, materials and rest rig outside the large cup's section 7. The original broad cup remained intact, with 6,400 inlet-detail triangles appended in that section. All six inlet parts passed closed-component and self-intersection checks and had no detected intersections with neutral skin, visor, hood or outer seal; minimum sampled inlet-to-visor clearance was approximately **0.562 mm**. Cup/seat/post contacts were intentional. The source inventory contained no images, text blocks or linked libraries. Both FBX/GLB exports passed geometry, section counts, material order, rigid Root weights and FBX roundtrip checks, bound to that version's source hash. All 32 static visibility combinations passed across the two variants and four independent toggles. UE cooking, native container integrity and all six cooked-asset audits passed, including both cooked meshes. Its four installed files matched the audited payload hashes. Historical reports are `assets/gas_mask_variant_validation.json` and `assets/gas_mask_runtime_validation.json`; static checks and live observations are recorded separately.

Live **1.2.0 revision 16** checks in **Stellar Blade 2.1 with CNS 2.2** confirmed both named meshes render and **Large oral-nasal cup → Scuba cup → Large oral-nasal cup** switching works; the original Scuba cup has no inlet discs. **Side Filters On → Off → On** switches both filters while the cup and inlet valves remain visible. **Inner Nasal Cup Off** hides the larger cup and both inlet valves together. The exterior chin **Valve** can be hidden independently, and **Hood On**, independent cup/visor colors and both opacity sliders work.

A full process exit, relaunch and **Continue**, followed by CNS readback, retained **Large oral-nasal cup**, **Cup/Valve/Hood/Side Filters all On**, **cyan glass**, **black cup**, **visor opacity 0.10** and **cup opacity 0.98**. See the [1.2.0 runtime report](../assets/gas_mask_runtime_validation.json). This inspection was limited to camp/idle and restart persistence; combat movement and extreme poses are not validated. After testing, the game was closed and the original saved CNS settings were restored byte-for-byte, verified by matching SHA-256 hashes.

**1.1.9 history:** independent source checks passed exact preservation of sections 0–10 and the Root rig, hood manifold topology, winding, and no detected skin/self intersections. The neutral fit was inspected in glossy and matte Blender views. Source/export checks passed 97,798 triangles, 12 slots, FBX roundtrip and rigid Root weights. Native container integrity, cooked geometry/connectivity and skeleton/material-reference checks passed. Its installation receipt records matching payload hashes and unchanged saved settings at installation. Retained 1.1.6 and 1.1.8 reports remain tied to historical hashes.

Live **1.1.9** checks in **Stellar Blade 2.1 with CNS 2.2** passed independent Cup/Valve/Hood toggles, visor opacity **0.10 → 0.99 → 0.10**, independent cyan visor/yellow cup presets, normal rendering and crown/ear/side/rear hood coverage. Hair was temporarily hidden through CNS for coverage screenshots; the mod leaves hair unchanged. A full close/relaunch and existing camp reload preserved **Hood On, Valve Off, Cup Off, cyan visor, black cup, visor opacity 0.10 and cup opacity 0.20**. See the [1.1.9 runtime report](../assets/runtime_validation.json).

Live inspection was limited to camp/idle, with persistence checks scoped to the versions described above. Broad combat movement, extreme poses and other heads remain untested. The accessory uses the rigid glasses Root attachment: its short hood cuff does not deform with neck motion or facial expressions.
