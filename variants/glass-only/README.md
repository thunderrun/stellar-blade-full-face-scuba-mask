# Full Face Scuba Mask — Glass Only optional release

Version **1.2.3-GlassOnly.1**, revision **21**, provides full-face continuous curved glass and an optional fitted latex hood for Eve in **Stellar Blade**. It has no inner cup, cup variants, exterior chin valve or valve opening. Hair is unchanged.

This optional package is standalone with **CNS**; no other mask mod is required. It replaces the regular Scuba or Roxane companion payload. Keep only one installed Scuba package.

## Download and use

Use `Full-Face-Scuba-Mask-CNS-1.2.3-GlassOnly.1.zip` from the mod's **Optional Files** on [Nexus Mods](https://www.nexusmods.com/stellarblade/mods/3872?tab=files). Install [Custom Nanosuit System 2.2](https://www.nexusmods.com/stellarblade/mods/1496) and its required UE4SS setup first.

With the game closed, back up the current four Scuba files outside `Paks`, then extract the archive's `SB` folder into the `StellarBlade` directory. Replace all four files in `SB/Content/Paks/~mods/CustomNanosuitSystem/Cosmetics/CodexScubaMask/`: the matching `CodexCNS-ScubaMask-947.pak/.ucas/.utoc` triple and `CodexCNS-ScubaMask.dekcns.json`. Do not keep a renamed second Scuba package in another mod folder. Restart after installation.

If **AiK : Mask Roxane SE** is still equipped from the companion setup, unequip it in CNS's **Earrings/Ears** category before checking this standalone mask. Leave its files and saved configuration intact.

Equip a vanilla pair of glasses to initialize Eyes if needed. Press **Alt+N**, select **Full Face Scuba Mask - Glass Only** in **glasses/Eyes**, and open its cog. It has one **Glass only** variant and a separate CNS identity, so set its preferences independently of previous Scuba items.

| Setting | Effect | Default |
| --- | --- | --- |
| Hood | Shows the full fitted glossy latex hood | Off |
| Glass Color | Changes the visor tint | Neutral |
| Visor Opacity | Adjusts opacity from 0.00 to 1.00 | 0.10 |

There are no Cup or Valve controls. The mod neither modifies nor hides hair.

## Geometry and verification

The source has **37,723 vertices**, **75,314 triangles** and **7 materials**. Glass accounts for **10,980 triangles**, Hood for **49,404**, and Hood Off leaves **25,910**. The cooked payload contains **8 custom asset packages** in **9 native chunks**. The download contains only this project's four payload files, `README.txt` and `package-manifest.json`.

Source/export/privacy checks and **all five cooked audits passed**. The full frame, glass and hood preserve the revision-19 positions, corner normals, weights, material definitions and rigid Root attachment. Glass and hood are single closed connected shells with Euler characteristics 2 and 0. Maximum measured cooked/source vertex difference is **0.0000298023 mm**, with zero Root position or rotation error. The four-file local installation was verified and saved settings were unchanged during installation.

A **user-provided in-game screenshot dated 2026-09-29** confirms rendering and the displayed Glass Only configuration: **Hood On**, **Visor Opacity 0.20**, **Glass Color**, and no Cup or Valve controls. The screenshot's opacity is a user setting; the shipped default remains **0.10**. This confirms rendering and UI only. Independent control-change, movement, combat and restart-persistence tests are not claimed for this optional release. The [runtime evidence record](runtime_validation.json) binds the screenshot hash to this source and payload.

The accessory follows the rigid glasses Root attachment. Its short hood cuff does not deform with neck motion or facial expressions, and fit can vary with hairstyle or pose. Older releases' runtime reports apply only to their recorded versions.

## Provenance

The package includes original project assets only. It does not include AiK assets, game fitting references, character meshes, game textures or diagnostic renders. CNS, UE4SS and Stellar Blade are separate dependencies. See the project's [provenance and dependencies](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/blob/main/ATTRIBUTION.md). No project license has been selected.
