# Optional Movement Breathing 0.2.9

A standalone UE4SS add-on for Stellar Blade. It plays recording #2 while walking, recording #3 while running, and raises #3's volume while sprinting. After confirmed walking or running stops, #2 continues at idle. Standing still at game/world startup is silent.

Download **Optional Movement Breathing**, version **0.2.9**, from the [GitHub release](https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/releases/tag/breathing-v0.2.9). The optional upload on the [Nexus Files page](https://www.nexusmods.com/stellarblade/mods/3872?tab=files) is currently quarantined by Nexus's automated checks and is unavailable there pending review. This component requires an existing working UE4SS setup. It works independently of CNS and the mask.

## Install and configure

Close the game, extract the downloaded ZIP, and run its `Install.ps1` from the extracted folder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
```

Pass `-GameRoot "D:\SteamLibrary\steamapps\common\StellarBlade"` for a custom game location. The installer checks the package and native container identity, rejects existing add-on folders, and verifies all seven installed files. For updates, first run the previous extracted package's installer with `-Uninstall`. Edited configurations are protected; keep a copy and resolve the old installation before updating.

The installed configuration is `SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath/Scripts/config.lua`.

| Setting | Default behavior |
| --- | --- |
| `IdleAfterMovement = true` | Keep #2 at idle only after confirmed walking/running |
| `Volume = 0.45` | Normal walking, running and armed idle volume |
| `SprintVolume = 0.75` | Louder #3 during sprint |
| `FadeInSeconds = 0.50` | Start transition |
| `CrossfadeSeconds = 0.75` | Walk/run/idle transition |
| `PollMilliseconds = 50` | Existing movement observation rate |

Set `IdleAfterMovement = false` to restore the original two-second #2 stop fade. `FadeOutSeconds` applies only in that mode. Held idle never re-arms playback. Walking-to-idle reuses the same voice; running-to-idle crossfades to #2. Observed blocked/airborne states and pawn lifecycle resets clear the movement arm. Native audio obeys game pause, including pauses that suppress actor ticks.

## Source and tests

`mod/Scripts/main.lua` drives audio from Eve's actor tick and lifecycle hooks. Only primitive identities survive callbacks. The current World/PersistentLevel/WorldSettings actor supplies a native owned-component list, matched by address and full name. Settled playback skips audio lookups, repeated Play calls and unchanged volume writes. The scheduler and lookup fix match the working v0.2.8 build; idle adds only movement-state logic in `running_state.lua`.

Tested with Python 3.12 and Lua 5.4 through Lupa. Install the Python dependencies and run from this component directory:

```powershell
python -m pip install -r requirements.txt
python checks/test_runtime.py
```

The **205 checks** execute the shipped Lua with mocked engine APIs and callback-bound wrappers. They cover startup silence, qualification thresholds, single persistent idle voice, transitions, volume caps, lifecycle/reload cleanup, zero steady-idle audio queries/setters, and optional original two-second stop fade. They do not replace listening or native stability tests.

The public [release validation](validation/release-validation.json) also records native SoundWave/container checks, installer and installed hashes, and the short gameplay check in which the user confirmed that v0.2.9 works very well. A controlled same-scene FPS comparison and long-session stability have not been established.

## Audio and packaging

The two prepared 48 kHz stereo PCM16 WAVs in `source/audio/` are 9.85-second loops with a 0.15-second seam crossfade. `release.json` records their original recording filenames and hashes; the source recordings are unchanged. No game or engine assets, mappings, compression DLLs or third-party tool binaries are included here.

Use `prepare_dual_audio.py` to verify the supplied loops or prepare replacements from your recordings. See [the UE audio recipe](ue/README.md) for import and native container auditing.

For a runtime-only rebuild, retain the three audited native audio files from an extracted Nexus v0.2.9 package, then run:

```powershell
python checks/test_runtime.py
python package_mod.py --audio-bundle "D:\Downloads\Codex-Running-Breath-0.2.9"
python checks/test_installer.py "build/packages/Codex-Running-Breath-0.2.9"
```

The packaging helper verifies the frozen audio SHA256 values and current source-bound Lua tests, creates the same seven-file install layout, and checks ZIP contents and hashes. It does not recook or install anything. Its rebuilt ZIP metadata/README can differ from the published Nexus archive; audio and runtime payload hashes remain comparable. Changing audio requires recooking and auditing the SoundWaves before updating `release.json`.

To remove the installed add-on, close the game and run its original package installer with `-Uninstall`. Only the seven matching files belonging to this component are removed.
