Optional Movement Breathing 0.2.9 for Stellar Blade

Requires an existing working UE4SS installation. Mask and CNS are optional.
Walking and idle after movement use recording #2. Running uses recording #3.
Sprint breathing is louder. Standing still at game/world startup is silent.
Idle becomes active only after confirmed walking/running followed by stopping.

INSTALL
Close Stellar Blade, extract this ZIP, and run Install.ps1 from this folder:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1
Pass -GameRoot "your StellarBlade folder" for a custom game location.
For updates, uninstall the previous add-on with its original installer first.
Existing folders and edited configurations are protected from overwrite/removal.

CONFIGURE
Edit SB/Binaries/Win64/ue4ss/Mods/CodexRunningBreath/Scripts/config.lua.
Volume defaults to 0.45; SprintVolume is 0.75. Start fade is 0.5 seconds and
walk/run/idle crossfade is 0.75 seconds. Steady idle reuses a single sound loop.
IdleAfterMovement=true enables #2 idle only after movement. Set it to false
to restore the original FadeOutSeconds=2 stop tail, then silence.

REMOVE
Close the game and run this package's Install.ps1 with -Uninstall.
Only the seven matching files belonging to this add-on are removed.

SOURCE, TESTS AND AUDIO BUILD RECIPE
https://github.com/thunderrun/stellar-blade-full-face-scuba-mask/tree/main/optional/running-breathing
The source release has 205 automated Lua behavior checks and a short user-
confirmed gameplay check. New source/audio edits require fresh validation.
The installer verifies payload hashes; tests do not prove every gameplay case
or long-session stability. This package does not include UE4SS or Unreal Engine.
