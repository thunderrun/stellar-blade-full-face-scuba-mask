# Full Face Mask & Breathing Sound

**Optional movement breathing:** [Running, walking, sprint and idle breathing 0.2.9](optional/running-breathing/README.md) is a separate UE4SS add-on. Idle breathing starts only after you walk or run and stop. It works independently of the mask and CNS. [Download the tested ZIP from GitHub](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/releases/download/breathing-v0.2.9/Codex-Running-Breath-0.2.9.zip). The optional copy on the [Nexus Files page](https://www.nexusmods.com/stellarblade/mods/3872?tab=files) is currently quarantined by Nexus's automated checks and is unavailable there pending review.

**Glass Only optional release:** [Full-face glass and fitted optional hood, version 1.2.3-GlassOnly.1](variants/glass-only/README.md) is available without an inner cup or valve. It requires CNS 2.2 and replaces the regular Scuba or companion package; keep only one installed Scuba payload. The regular 1.2.2 source and instructions below remain separate.

![Version 1.2.2 with the tighter hood and hair visible in Stellar Blade 2.1 and CNS 2.2](media/tight-hood-in-game.jpg)

The optional hood now fits closer beneath hair. The mod neither modifies nor hides hair.

The preview is the paused ear/temple fit check. Compare [hood on](media/runtime-1.2.2/02-tight-hood-on-current-hair.jpg) with [hood off](media/runtime-1.2.2/03-tight-hood-off-current-hair.jpg); [Noble Elegance](media/runtime-1.2.2/05-noble-elegance-normal-physics.jpg) was also checked after normal simulation resumed. The runtime report records the pause-related background artifacts and test limits.

An original, strapless full-face mask accessory fitted for Eve in **Stellar Blade**, for use with CNS. This repository contains editable geometry and export/build scripts. It does not include the game's character mesh, textures, original glasses mesh, or Unreal Engine.

Version **1.2.2** fits the optional latex hood closer around the temples, ears, scalp and back of the head to reduce interference with hair. The two side filters and their CNS option have been removed. **Scuba cup** and the smoother **Large oral-nasal cup** retain their 1.2.1 geometry; the larger cup still includes **two small inlet valves on the inner cup**, sharing its material, color, opacity and visibility. The oval visor, strapless frame, independent cup/chin Valve/Hood toggles, colors and opacity controls remain. Hair is unchanged.

Both variants use **12 material slots**. The Scuba cup mesh has **97,798 triangles** and the larger variant has **127,646 triangles**. They differ only in cup section 7: the larger cup contains a 40,396-triangle smoothed body plus 6,400 triangles for its two inlet-valve assemblies. Both include the 49,404-triangle hood and retain the single-Root glasses attachment.

## Download and use

Download the [**1.2.2 package**](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/releases/download/v1.2.2/Full-Face-Scuba-Mask-CNS-Tight-Hood-1.2.2.zip) or read its [release notes](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/releases/tag/v1.2.2). The [Nexus Mods page](https://www.nexusmods.com/stellarblade/mods/3872) has not been updated. Install [Custom Nanosuit System 2.2](https://www.nexusmods.com/stellarblade/mods/1496) and its required UE4SS setup first.

With the game closed, extract the complete package's `SB` folder into the `StellarBlade` directory. Replace all four mask files in `SB/Content/Paks/~mods/CustomNanosuitSystem/Cosmetics/CodexScubaMask/`. Install the matching PAK/UCAS/UTOC triple and current JSON together. The tighter hood and removal of filter geometry require rebuilt mesh archives; a JSON-only update is insufficient. Keep only one installed copy and restart the game after installation. To build from source, follow the [UE recipe](ue/README.md).

Equip a vanilla pair of glasses to initialize Eve's Eyes component, press **Alt+N**, select Eve and choose **Full Face Scuba Mask** in the glasses/Eyes category. Use the item's variant arrows to select **Scuba cup** or **Large oral-nasal cup**. Open its **cog/configuration** menu for independent settings:

| Setting | Effect | Default |
| --- | --- | --- |
| Inner Nasal Cup | Shows the selected cup, its collar and the larger cup's inlet valves | On |
| Valve | Shows the exterior chin valve assembly | On |
| Hood | Shows the glossy black latex hood | Off |
| Glass Color / Inner Cup Color | Colors the visor and cup independently | Neutral glass / cup |
| Visor Opacity / Cup Opacity | Adjusts each surface independently | 0.10 / 0.20 |

Use the color swatches or picker for custom colors. Each setting colors both sides of its surface together. At low opacity, tints are subtle; increase the corresponding opacity to make them more visible. The opacity range is **0.00–1.00** in 0.01 steps. Reflections and Fresnel effects remain, so zero opacity need not remove every reflection; use the cup toggle to hide its geometry completely. Turning Valve Off leaves the cup collar and the visor's existing valve opening in place.

If new controls are missing after restarting, reset only this mask through **Reset Configuration** in its configuration panel; this also resets its saved settings.

The hood covers the scalp, ears, sides and back of the head, continues beneath the chin, and ends in a short neck cuff. Its face opening sits beneath the mask seal. The cuff follows the rigid head attachment and does not deform with neck motion or facial expressions.

## Files

| Path | Purpose |
| --- | --- |
| `assets/full_face_mask.blend` | Editable components, two optimized game meshes and one-bone rig; no game fitting references |
| `assets/SK_CodexScubaMask.fbx` / `.glb` | Scuba cup variant; FBX uses centimetres and GLB uses metres |
| `assets/SK_CodexGasMask.fbx` / `.glb` | Large oral-nasal cup variant with the same material and rig contract |
| `assets/asset_manifest.json` | Scuba export contract and additional variant registration |
| `assets/gasmask_variant_manifest.json` | Large cup export contract |
| `assets/material_spec.json` | Blender preview material values |
| `assets/export_validation.json` | Main source inventory and FBX/GLB checks |
| `assets/gasmask_export_validation.json` | Large-cup source inventory and FBX/GLB checks |
| `assets/tight_hood_validation.json` | 1.2.2 hood fitting, filter removal and preservation report |
| `assets/tight_hood_runtime_validation.json` | 1.2.2 hair-visible fit, variants, controls and CNS menu-reopen checks |
| `assets/smooth_cup_validation.json` | Historical 1.2.1 shape, neutral fitting and preservation report |
| `assets/smooth_cup_runtime_validation.json` | Historical 1.2.1 live shape, variants, controls and CNS menu-reopen checks |
| `assets/gas_mask_variant_validation.json` | Historical 1.2.0 source, fitting and preservation report |
| `assets/gas_mask_runtime_validation.json` | Historical 1.2.0 live variant, controls and restart-persistence checks |
| `assets/hood_validation.json` | Historical 1.1.9 hood topology, neutral fitting and mask preservation |
| `assets/runtime_validation.json` | Historical 1.1.9 live controls, coverage and restart persistence |
| `assets/valve_toggle_validation.json` | Historical 1.1.8 valve-section checks |
| `assets/cup_fit_validation.json` / `under_chin_validation.json` | Historical 1.1.5 fitting and underside reports |
| `assets/valve_connection_validation.json` | Historical 1.1.4 passage/contact report |
| `assets/integrated_cup_geometry_validation.json` / `integrated_cup_validation.json` | Historical 1.1.6 geometry and independent 17-check review |
| `scripts/export_mask.py` | Repeatable export and validation of both mesh variants |
| `cns/CodexCNS-ScubaMask.dekcns.json` | CNS variants, independent toggles, colors and linked opacity sliders |
| `ue/` | UE 4.26 import/cook recipe and material parameter contract |

Historical reports validate only their recorded source/export hashes. They do not certify later geometry or runtime behavior.

## Open or export the model

Tested with Blender **5.2.1**. Open `assets/full_face_mask.blend`. Named visible components are editable; the hidden export meshes are `SK_CodexScubaMask` and `SK_CodexGasMask`. Both are rigidly weighted to the single `Root` bone.

Run from the repository directory with Blender on your `PATH`:

```powershell
blender --background --python scripts/export_mask.py
blender --background --python scripts/export_mask.py -- --validate-only
```

The exporter processes the main manifest and its additional variant. It verifies positions, triangle counts, material order, section separation, Root weights/rest pose, opacity and absence of external image dependencies. It leaves the `.blend` unchanged. Export bytes can vary with exporter versions and timestamps; geometry and rig checks are the reproducibility target.

Editing a visible component does **not** automatically update either optimized mesh. Update the appropriate export mesh and manifest together. Keep the armature named `Armature`; preserve the rest transform, centimetre coordinates and material order. The two variants must match exactly outside cup section 7.

| Section | Geometry | Scuba cup triangles | Large cup triangles |
| --- | --- | --- | --- |
| 0–10 | Mask, including the selected cup | 48,394 | 78,242 |
| 7, within the above total | Cup, seal and collar; large cup also includes inlet valves | 16,948 | 46,796 |
| 8, within the above total | Complete outer visor and lower faceplate | 11,450 | 11,450 |
| 1, 4, 9, 10, within the above total | Independently hideable chin valve | 5,066 | 5,066 |
| 11 | Latex hood | 49,404 | 49,404 |
| Total | All sections, including hidden options | 97,798 | 127,646 |

With Hood Off, the Scuba cup variant has 31,446 triangles with Cup Off, 43,328 with Valve Off, and 26,380 with both hidden. The larger variant adds its inlet-valve geometry to section 7, so Cup Off hides those valves together with the cup. Hood adds 49,404 triangles independently. Hiding either cup must leave the outer visor closed.

The Scuba cup retains the broad lower chamber and short 18 mm inner / 20 mm outer diameter valve collar from 1.1.6. The larger variant keeps the collar and through-bore in place while rounding its bridge, cheeks and mouth bowl. Local subdivision lets the lower transition curve without folding the thin shell; a small contact-flange transition remains above the fixed collar. Two shallow round inlet-valve details sit on the larger cup's cheek wings, inside the visor, and belong to the same cup material section. They are present only with Large oral-nasal cup selected and visible. These are artistic fitting dimensions and details for a game asset.

## Build and package the game accessory

See [the UE build instructions](ue/README.md). You need your own Unreal Engine **4.26.2**, Stellar Blade and CNS installations. The build creates two skeletal meshes and 12 shared material instances: **14 custom asset packages** inside one selected PAK/UCAS/UTOC triple. Local placeholders for game dependencies are excluded from that chunk. No generated engine or game assets are included in `ue/`.

The two `OutfitPaths` and matching `OutfitNames` select the cup mesh while preserving the existing `UniqueFitID`. `VectorControls` exposes Glass Color on slot 8 and Inner Cup Color on slot 7. Each visible `GlassColor Out` writes its hidden `GlassColor In` partner through `ControlledBy`. Neutral RGBA defaults remain `[0.12, 0.12, 0.12, 1]` for glass and `[0.18, 0.18, 0.18, 1]` for the cup. Old color-preset `OutfitDatas` overrides remain absent.

Opacity controls link each hidden `Opacity Inner` to visible `Opacity Out`. Valve links sections 1, 4, 9 and 10; Hood controls 11. Cup uses section 7 in either variant, including the inlet valves on the larger cup. Side Filters and sections 12–13 have been removed; all surviving controls retain their existing IDs and defaults. See the [CNS advanced configuration schema](https://github.com/Dekita/SB-CustomNanosuitSystem-Docs/blob/main/guides/cns-json-advanced.md).

Inspect the selected chunk, then package its archives as `CodexCNS-ScubaMask-947.pak/.utoc/.ucas` with the current CNS JSON. Install all four together. Preserve the item ID and existing controls when extending the configuration. `scripts/package_color_variants.py` is a historical **1.1.2 preset-only** helper and is incompatible with this build. `scripts/export_mask.py --manifest` supports isolated draft validation.

## Scope and verification

**1.2.2, revision 18:** the final hood donor passed independent closed-manifold, winding, finite-coordinate, nondegenerate-triangle and smooth-shading checks, with no detected self or neutral-skin intersections. Matched glossy and matte views show the reduced temple/ear volume and smoother lower-side transition. Median sampled nearest-skin distance decreased from approximately **3.40 to 0.81 mm at the temple**, **8.01 to 1.81 mm around the ear**, and **9.29 to 1.94 mm at the lower side**. These regional samples describe the neutral fit, not continuous global clearance or animated hair compatibility. Final source checks confirmed exact preservation of mask sections 0–10 in both variants, including the cups and inlet valves, and removal of the filter geometry, materials and control. Both exports and all 16 static visibility combinations passed. UE cooking and all seven post-build audits passed; the four locally installed files match the audited payload, and saved settings were unchanged during installation. The current source and runtime reports are `assets/tight_hood_validation.json` and `assets/tight_hood_runtime_validation.json`.

Live **1.2.2 revision 18** checks after a fresh launch in **Stellar Blade 2.1 with CNS 2.2** confirmed both named cup variants render and the Side Filters row is absent. **Hood Off/On** was checked with the current brown ponytail/bangs and **Noble Elegance**, keeping hair visible over the hood. The former broad temple bulge was reduced to a small fitted ear cover. The gas cup and its two inlet valves hide and return together through **Inner Nasal Cup**; the exterior chin **Valve** switches independently, and cup opacity works.

Closing CNS to gameplay and reopening it retained **Large oral-nasal cup**, **Cup On**, **Valve Off**, **Hood On**, **visor opacity 0.25** and **cup opacity 0.97**. Testing covered camp/idle and CNS menus. Full-game restart persistence, combat, extreme poses and all-hairstyle compatibility were not tested for 1.2.2. Hair remains unchanged; these two hairstyle checks do not guarantee clearance for every hairstyle or animated pose. After closing the game, the pre-test CNS settings were restored byte-for-byte and verified by matching SHA-256 hashes; other game save writes were preserved. See the [1.2.2 runtime report](assets/tight_hood_runtime_validation.json).

**1.2.1, revision 17 history:** the smoothed cup passed closed-component, winding, finite-coordinate, nondegenerate-triangle and self-intersection checks, with no detected intersections against neutral skin, visor, hood or outer seal. The fixed collar region is preserved. Dense cup-body sampling measured minimum clearances of approximately **0.382 mm to skin** and **0.512 mm to visor**; these sampled distances are not continuous global minima. Independent glossy and matte front, three-quarter, profile and detail review accepted the rounder bridge and bowl, with the retained lower contact-flange transition. Final-source checks passed exact preservation of the Scuba variant, all gas-mask sections outside cup 7, materials, Root rig and CNS configuration. Both FBX/GLB exports passed and bind the integrated source hash; all 32 static toggle combinations passed. UE cooking and all seven post-build audits passed, and guarded local installation completed.

Live **1.2.1 revision 17** checks after a fresh launch in **Stellar Blade 2.1 with CNS 2.2** confirmed normal full-mask rendering and the rounded gas cup with paired inlet valves. **Scuba cup → Large oral-nasal cup → Scuba cup → Large oral-nasal cup** switching passed. **Inner Nasal Cup Off → On** hid and restored the cup and both inlets together; **Side Filters Off → On → Off → On** switched the filters independently. Hood On, cup opacity **0.20 → 0.98**, and a cyan visor with neutral then black cup color were inspected. Hair and the hairpin were temporarily hidden through CNS.

Closing and reopening CNS retained **Large oral-nasal cup**, **Cup/Valve/Hood/Side Filters all On**, **cyan glass**, **black cup**, **visor opacity 0.10** and **cup opacity 0.98**. Full-game restart persistence was **not retested for 1.2.1**. Testing covered camp/idle, with no combat or extreme-pose sweep. After closing the game, the original saved CNS settings were restored byte-for-byte and verified by matching SHA-256 hashes. See the [1.2.1 runtime report](assets/smooth_cup_runtime_validation.json).

**1.2.0, revision 16 history:** independent source checks passed preservation of the original mask, hood, filters, materials and rig, with the two variants differing only in cup section 7. The six new inlet parts—two seats, two thin flaps and two retaining posts—passed closed-component and self-intersection checks, with no detected intersections against the neutral skin, visor, hood or outer seal. Their minimum sampled visor clearance was approximately **0.562 mm**; contacts with the cup and between retaining posts/flaps were intentional. The original broad-cup geometry remained intact beneath the added details. The source inventory contained no images, text blocks or linked libraries. Both FBX/GLB exports passed geometry, section counts, material order, rigid Root weights and FBX roundtrip checks. Static visibility counts passed all 32 combinations across the two variants and four independent toggles. UE cooking, native container integrity and all six cooked-asset audits passed. Its four locally installed files matched the audited payload hashes. Static checks and installation readback were recorded separately from the live observations below.

Live **1.2.0 revision 16** checks in **Stellar Blade 2.1 with CNS 2.2** confirmed both named meshes render and **Large oral-nasal cup → Scuba cup → Large oral-nasal cup** switching works; the original Scuba cup has no inlet discs. **Side Filters On → Off → On** switches both filters while the cup and inlet valves remain visible. **Inner Nasal Cup Off** hides the larger cup and both inlet valves together. The exterior chin **Valve** can be hidden independently, and **Hood On**, independent cup/visor colors and both opacity sliders work.

A full process exit, relaunch and **Continue**, followed by CNS readback, retained **Large oral-nasal cup**, **Cup/Valve/Hood/Side Filters all On**, **cyan glass**, **black cup**, **visor opacity 0.10** and **cup opacity 0.98**. See the [1.2.0 runtime report](assets/gas_mask_runtime_validation.json). This inspection was limited to camp/idle and restart persistence; combat movement and extreme poses are not validated. After testing, the game was closed and the original saved CNS settings were restored byte-for-byte, verified by matching SHA-256 hashes.

**1.1.9 history:** every original mask section 0–10 retained coordinates, corner normals, UVs, Root weights and material definitions. Independent checks confirmed a closed manifold hood without detected skin or nonadjacent self-intersections against the private neutral head. Source/export validation passed for 97,798 triangles, 12 material slots, FBX roundtrip and rigid Root weights. Native container integrity, cooked geometry/connectivity and skeleton/material-reference checks passed. Its installation receipt records matching payload hashes and unchanged saved settings at installation.

Live **1.1.9** tests in **Stellar Blade 2.1 with CNS 2.2** confirmed independent Cup/Valve/Hood toggles, visor opacity **0.10 → 0.99 → 0.10**, independent cyan visor/yellow cup presets, normal rendering and crown/ear/side/rear hood coverage. Hair was temporarily hidden in CNS for inspection. A full game close and relaunch, followed by loading the existing camp save, retained **Hood On, Valve Off, Cup Off, cyan visor, black cup, visor opacity 0.10 and cup opacity 0.20**. See the [1.1.9 runtime report](assets/runtime_validation.json).

Live inspection was limited to camp/idle, with persistence checks scoped to the versions described above. Broad combat movement, other heads and extreme poses remain untested. The accessory retains its rigid glasses Root attachment; the short hood cuff does not deform with neck motion or facial expressions. The private Eve fitting reference is not included, and the mod neither modifies nor hides hair.

The original geometry draws design inspiration from the separate nose cup of [Dräger X-plore 5500](https://www.draeger.com/Content/Documents/Products/x-plore-5500-pi-DMC-113276-en-us.pdf), the panoramic visor and interchangeable nosecups of [Avon FM54](https://www.avon-protection.com/media/ue1iluwy/avon-protection_fm54-respirator_product-brochure_en.pdf), and the distinction between breathing cavity and flexible chin seal in [Avon's respirator patent](https://patents.google.com/patent/WO2024074487A1/en). No manufacturer model, texture or logo is included. See [provenance and dependencies](ATTRIBUTION.md). No project license has been selected yet.
