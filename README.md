# Full Face Scuba Mask

![Full Face Scuba Mask on Eve in CNS](media/in-game.jpg)

An original full-face mask accessory fitted for Eve in **Stellar Blade**, intended for use with CNS. This repository contains editable mask geometry and the export/build scripts. It does not include the game's character mesh, textures, original glasses mesh, or Unreal Engine.

Version **1.1.1** retains the version 1.1 model and **Inner Nasal Cup** On/Off control, and adds separate **Visor Opacity** and **Cup Opacity** sliders in CNS. The black frame, under-chin silicone seal, complete outer faceplate and opaque chin valve stay visible in both states. There are no inner valves, head straps, hose, snorkel or logos. Default outer visor opacity is **10%**; the cup defaults to **20%** when shown. Both are adjustable from 0% to 100%. The experimental 1.2 oral-cup/mouthpiece redesign has been reverted.

## Download and use

The [Nexus Mods download](https://www.nexusmods.com/stellarblade/mods/3872) remains at **1.1.0**. The **1.1.1 opacity configuration is on GitHub only** for now. For a new installation, install [Custom Nanosuit System 2.2](https://www.nexusmods.com/stellarblade/mods/1496) and its required UE4SS setup first. With the game closed, copy the Nexus archive's four mod files into `StellarBlade/SB/Content/Paks/~mods/CustomNanosuitSystem/Cosmetics/CodexScubaMask/`. Remove duplicate older main/no-inner-cup copies installed elsewhere.

After installing 1.1.0 (or if it is already installed), replace only its `CodexCNS-ScubaMask.dekcns.json` with [the updated configuration](cns/CodexCNS-ScubaMask.dekcns.json), then restart the game once so CNS reloads its cached configuration. The three binary mod files are unchanged.

Start the game, equip a vanilla pair of glasses to initialize Eve's Eyes component, then press **Alt+N**, select Eve and choose **Full Face Scuba Mask** in the glasses/Eyes category. It uses the same component as other glasses accessories.

Open the item's **cog/configuration** controls. **Inner Nasal Cup** switches the cup On/Off (default On); **Visor Opacity** and **Cup Opacity** adjust transparency independently. The raw slider range is **0.00–1.00**, equivalent to **0–100%**, in 0.01 steps. Defaults are 0.10 and 0.20. Each slider changes both inside and outside surface opacity. Reflections and Fresnel effects are unchanged, so 0 does not necessarily remove every reflection; use the cup toggle to hide its geometry completely. After the initial configuration update/restart, slider adjustments need no file swaps. If an older saved configuration hides the new controls, use **Reset Configuration** in the item's configuration panel.

## Files

| Path | Purpose |
| --- | --- |
| `assets/full_face_mask.blend` | Editable mask components, optimized game mesh and one-bone rig; no game fitting references |
| `assets/SK_CodexScubaMask.fbx` | 38,966-triangle skeletal game mesh, centimetres, one `Root` bone |
| `assets/SK_CodexScubaMask.glb` | Portable mask preview/export, metres |
| `assets/material_spec.json` | Blender preview material values |
| `assets/asset_manifest.json` | Export dimensions/slot contract and external skeleton reference |
| `assets/export_validation.json` | Source inventory and FBX/GLB checks for the included exports |
| `scripts/export_mask.py` | Repeatable selection, export and validation |
| `cns/CodexCNS-ScubaMask.dekcns.json` | Custom-authored CNS registration, cup toggle and linked opacity sliders |
| `ue/` | Text-only UE 4.26 import/cook recipe and game material parameter contract |

## Open or export the model

Tested with Blender **5.2.1**. Open `assets/full_face_mask.blend`. The visible `MASK` collection contains individually named editable components. The hidden `EXPORT` collection contains `SK_CodexScubaMask`, the optimized mesh used by the exporter. Both are rigidly weighted to the single `Root` bone.

Run from the repository directory with Blender on your `PATH`:

```powershell
blender --background --python scripts/export_mask.py
blender --background --python scripts/export_mask.py -- --validate-only
```

The first command regenerates FBX/GLB and verifies geometry positions, triangle counts, material order, cup-toggle section separation, Root weights/rest pose, opacity and absence of external image dependencies. It leaves the `.blend` unchanged. Export bytes can vary with exporter versions and file timestamps; geometry and rig checks are the reproducibility target.

The authoring components and optimized mesh are separate. Editing a visible component does **not** automatically update the optimized mesh: update `SK_CodexScubaMask` as part of your edit and adjust the triangle counts in `asset_manifest.json` when appropriate. Keep the armature object named `Armature`; preserve the rest transform, centimetre source coordinates and material order for game integration.

Cup/rims use material index **7** (`M_Scuba_NasalCup`, 7,990 triangles). The complete outer visor, including the lower faceplate, uses index **8** (`M_Scuba_Visor`, 10,980 triangles). The other seven sections are unchanged. CNS hides section 7 directly; lowering glass opacity to zero is not the toggle mechanism. Keep section 8 visible so Cup Off retains a closed shell. Cup Off shows 30,976 triangles, matching the earlier no-inner-cup variant.

## Build the game accessory

See [the UE build instructions](ue/README.md). You need your own installation of Unreal Engine **4.26.2**, Stellar Blade, and CNS. The project generates local placeholders at the game's required skeleton/material paths, but excludes those placeholders from the selected custom chunk. Only text/code is checked into `ue/`; no generated engine or game assets are included here.

CNS `ScalarControls` links each hidden `Opacity Inner` control to its visible `Opacity Out` control through `ControlledBy`, so the user sees one slider per transparent part. No mesh or material recook is needed. Game shader opacity uses separate inner/outer scalar parameters. `ue/manifest.json` sets both visor values to `0.10` and both nasal cup values to `0.20`. Blender/glTF previews approximate that shader and may look different under different lighting.

## Scope and verification

The included mask-only source retains every vertex and triangle from the final fitted revision 8 model. Version 1.1.0 only reassigns 1,212 lower exterior triangles from cup to visor material, keeping them visible when the cup is hidden. Its fitting reference was deliberately removed for distribution. The original local fit/audit checked the neutral face pose and under-chin placement; this repository cannot rerun character-clearance tests without a separately obtained local reference. Facial animation, alternate heads and extreme poses can change clearance. Source/cooked checks passed. Version 1.1.1 changes only the JSON controls and documentation; its existing mesh/material archives are byte-identical to 1.1.0. The scalar fields and parameter names were checked against installed CNS 2.2 and the native material contract. Live slider behavior and persistence still need in-game verification.

See [provenance and dependencies](ATTRIBUTION.md). No project license has been selected yet.
