return {
    Enabled = true,
    Volume = 0.45,
    SprintVolume = 0.75,
    Pitch = 1.0,
    RunStartSpeedCmPerSecond = 300.0,
    RunStopSpeedCmPerSecond = 220.0,
    UseSprintFlag = true,
    -- Speed hysteresis is a fallback when this game's bSprint is unavailable.
    SprintStartSpeedCmPerSecond = 700.0,
    SprintStopSpeedCmPerSecond = 600.0,
    WalkStartSpeedCmPerSecond = 50.0,
    WalkStopSpeedCmPerSecond = 25.0,
    StartHoldSeconds = 0.15,
    FadeInSeconds = 0.50,
    -- Reuse #2 at idle only after confirmed walking/running; startup stays silent.
    IdleAfterMovement = true,
    -- Used only with IdleAfterMovement=false to restore the original stop fade.
    FadeOutSeconds = 2.00,
    CrossfadeSeconds = 0.75,
    SprintFadeSeconds = 0.50,
    PollMilliseconds = 50,
    GroundedOnly = true,
    EvePawnNameContains = "CH_P_EVE",
    RunSoundAsset = "/Game/CodexRunningBreath/Audio/SW_RunBreathingLoop.SW_RunBreathingLoop",
    WalkSoundAsset = "/Game/CodexRunningBreath/Audio/SW_WalkBreathingLoop.SW_WalkBreathingLoop",
    DebugLogging = false,
}
