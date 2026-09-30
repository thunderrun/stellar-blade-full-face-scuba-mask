-- Codex Running Breath 0.2.9. Independent of CNS and all equipment.
-- Runtime UObject/audio work is driven by Eve's actor lifecycle hooks.
local C = require("config")
local UEHelpers = require("UEHelpers")
local State = require("running_state").new(C)
local PREFIX = "[CodexRunningBreath] "
local statics, pawnName = nil, nil
local MODES = { "walk", "run" }
local voices = {
    walk = { asset = C.WalkSoundAsset, sharedKey = "CodexRunningBreathActiveAudioPathWalk", retryAt = 0 },
    run = { asset = C.RunSoundAsset, sharedKey = "CodexRunningBreathActiveAudioPathRun", retryAt = 0 },
}
local assetHelpers = nil
-- The native engine class is rooted. Transient levels, actors and audio
-- components are resolved fresh and never cached across callbacks.
local audioComponentClass = nil
local elapsed, lastErrorAt = 0, -100
local initialized = false
local gameplayTickLogged = false
local lastPhase, lastMode = nil, nil
-- Shared variables retain raw UObject pointers across Lua reloads. Store only a
-- path string so a destroyed voice is looked up safely instead of reconstructed.
local SINGLE_SHARED_AUDIO_KEY = "CodexRunningBreathActiveAudioPath"
local OLD_SHARED_AUDIO_KEY = "CodexRunningBreathActiveAudio"
local function log(message) print(PREFIX .. message .. "\n") end
local function valid(object) return object ~= nil and object:IsValid() end
local function matchesIdentity(object, address, fullName, voice, stage)
    if not valid(object) then
        voice.failureReason = stage .. ": invalid result; expected " .. fullName .. " address=" .. tostring(address)
        return false
    end
    local currentAddress, currentFullName = object:GetAddress(), object:GetFullName()
    if currentAddress ~= address or currentFullName ~= fullName then
        voice.failureReason = string.format("%s identity mismatch: expected %q address=%s; found %q address=%s",
            stage, fullName, tostring(address), currentFullName, tostring(currentAddress))
        return false
    end
    return true
end
local function resolveAudio(voice, pawn)
    if not voice.audioPath then return nil end
    if not pawn then voice.failureReason = "context: no fresh pawn"; return nil end
    -- ReceiveEndPlay supplies a still-present contextual pawn before component
    -- teardown, even if IsValid is already false because it is pending kill.
    -- A pawn can belong to a streaming level. Its audio owner belongs to the
    -- persistent level, so derive that level from the current world instead.
    local world = pawn:GetWorld()
    if not valid(world) then voice.failureReason = "world: invalid current World"; return nil end
    local level = world.PersistentLevel
    if not matchesIdentity(level, voice.levelAddress, voice.levelFullName, voice, "level") then return nil end
    -- CreateSound2D's world parameters select WorldSettings as the owner.
    -- Both persistent-level properties are also used by installed UEHelpers;
    -- read them directly here without its cached world/controller wrappers.
    local owner = level.WorldSettings
    if not matchesIdentity(owner, voice.ownerAddress, voice.ownerFullName, voice, "WorldSettings owner") then return nil end
    if not valid(audioComponentClass) then audioComponentClass = StaticFindObject("/Script/Engine.AudioComponent") end
    if not valid(audioComponentClass) then voice.failureReason = "native class: AudioComponent unavailable"; return nil end
    -- UE4SS's name search can confuse numbered instances. Enumerate only this
    -- actor's owned audio components through the engine's reflected function.
    local components = owner:K2_GetComponentsByClass(audioComponentClass)
    -- This UE4SS build marshals a UFunction's array return as a 1-based Lua
    -- table of RemoteUnrealParam elements, unlike an array property accessor.
    if type(components) ~= "table" then voice.failureReason = "owned audio list: unexpected return type " .. type(components); return nil end
    local object, mismatch = nil, nil
    for _, element in ipairs(components) do
        local candidate = element:get()
        if valid(candidate) and candidate:GetAddress() == voice.audioAddress then
            local fullName = candidate:GetFullName()
            if fullName == voice.audioFullName then
                object = candidate
                break
            else
                mismatch = string.format("audio identity mismatch: expected %q address=%s; found %q at that address",
                    voice.audioFullName, tostring(voice.audioAddress), fullName)
            end
        end
    end
    if not object then
        voice.failureReason = mismatch or string.format("owned audio list: no identity match in %d entries; expected %q address=%s",
            #components, voice.audioFullName, tostring(voice.audioAddress))
        return nil
    end
    voice.lookupMethod = "owner-components"
    voice.lookupFailed = false
    voice.failureReason = nil
    return object
end
local function lookupFailed(mode)
    local voice = voices[mode]
    if not voice.lookupFailed then
        log("Cannot resolve owned " .. mode .. " audio component; replacement is blocked to prevent duplicate loops.")
    end
    if voice.failureReason and not voice.failureReasonLogged then
        log("Lookup failure " .. mode .. ": " .. voice.failureReason)
        voice.failureReasonLogged = true
    end
    voice.lookupFailed = true
end
local function clearVoice(mode)
    local voice = voices[mode]
    voice.audioPath, voice.audioAddress, voice.audioFullName, voice.audioShortName, voice.gain = nil, nil, nil, nil, 0
    voice.ownerName, voice.ownerAddress, voice.ownerFullName, voice.levelAddress, voice.levelFullName = nil, nil, nil, nil, nil
    if ModRef then
        ModRef:SetSharedVariable(voice.sharedKey, nil)
        ModRef:SetSharedVariable(voice.sharedKey .. "Address", nil)
        ModRef:SetSharedVariable(voice.sharedKey .. "FullName", nil)
    end
end
local function stop(mode, pawn, freshAudio)
    if not mode then
        for _, name in ipairs(MODES) do stop(name, pawn) end
        return
    end
    local voice = voices[mode]
    if not voice.audioPath then return end
    local previous = freshAudio or resolveAudio(voice, pawn)
    if valid(previous) then
        local ok = pcall(function() previous:Stop() end)
        if ok then
            clearVoice(mode); voice.lookupFailed = false
            if C.DebugLogging then log("Stopped " .. mode .. " breathing loop") end
        else lookupFailed(mode) end
    else
        -- An unresolved voice might still be playing. Retain its identity and
        -- block another creation until it can be found and stopped safely.
        lookupFailed(mode)
    end
end
local function setPawnName(name)
    if pawnName ~= name and C.DebugLogging then log("Pawn: " .. (name or "<none>")) end
    pawnName = name
end
local function reportPhase(observation, gains, phase, mode)
    if (phase ~= lastPhase or mode ~= lastMode) and C.DebugLogging then
        log(string.format("State %s (target=%s): speed=%.1f cm/s, eligible=%s, walkGain=%.3f, runGain=%.3f",
            phase, mode or "idle", observation.speed, tostring(observation.eligible), gains.walk, gains.run))
    end
    lastPhase, lastMode = phase, mode
end
local function errorLog(message)
    if elapsed - lastErrorAt >= 10 then
        log(message)
        lastErrorAt = elapsed
    end
end
assert(C.Volume >= 0 and C.Volume <= 1, "Volume must be in [0,1]")
assert(C.SprintVolume >= C.Volume and C.SprintVolume <= 1, "Sprint volume must be between Volume and 1")
assert(C.RunStartSpeedCmPerSecond >= C.RunStopSpeedCmPerSecond and
       C.RunStopSpeedCmPerSecond > C.WalkStartSpeedCmPerSecond and
       C.WalkStartSpeedCmPerSecond >= C.WalkStopSpeedCmPerSecond and C.WalkStopSpeedCmPerSecond >= 0,
       "Invalid walk/run speed thresholds")
assert(C.SprintStartSpeedCmPerSecond >= C.SprintStopSpeedCmPerSecond and
       C.SprintStopSpeedCmPerSecond >= C.RunStartSpeedCmPerSecond, "Invalid sprint speed thresholds")
assert(C.PollMilliseconds >= 25 and C.PollMilliseconds <= 500, "Invalid polling interval")
assert(C.FadeInSeconds >= 0 and C.FadeOutSeconds >= 0 and C.CrossfadeSeconds >= 0 and
       C.SprintFadeSeconds >= 0 and C.StartHoldSeconds >= 0,
       "Invalid timing")
local dt = C.PollMilliseconds / 1000

local function observe(pawn, localController)
    if not valid(pawn) then return nil, { eligible = false, speed = 0 } end
    -- The current tick supplies a live pawn; do not use UEHelpers' cached
    -- PlayerController wrapper across level changes and garbage collection.
    local controller = localController or pawn.Controller
    if not valid(controller) then return nil, { eligible = false, speed = 0 } end
    if not localController and not controller:IsLocalPlayerController() then return pawn, { eligible = false, speed = 0 } end
    local name = pawn:GetFullName()
    if pawnName and pawnName ~= name then
        stop(nil, pawn); State:reset()
    end
    setPawnName(name)
    if C.EvePawnNameContains ~= "" and not string.find(name, C.EvePawnNameContains, 1, true) then
        return pawn, { eligible = false, speed = 0 }
    end
    if string.find(name, "/Game/Lobby/", 1, true) or string.find(name, "/Temp/", 1, true) then
        return pawn, { eligible = false, speed = 0 }
    end
    if not valid(statics) then statics = UEHelpers.GetGameplayStatics() end
    if not valid(statics) then error("GameplayStatics is unavailable") end
    local blocked = statics:IsGamePaused(pawn) or controller:IsMoveInputIgnored()
    local grounded = true
    if C.GroundedOnly then
        local movement = pawn:GetMovementComponent()
        grounded = valid(movement) and movement:IsMovingOnGround()
    end
    local velocity = pawn:GetVelocity()
    local speed = math.sqrt(velocity.X * velocity.X + velocity.Y * velocity.Y)
    local sprinting = nil
    if C.UseSprintFlag then
        local ok, value = pcall(function() return pawn.bSprint end)
        if ok and type(value) == "boolean" then sprinting = value end
    end
    return pawn, { eligible = C.Enabled and not blocked and grounded, speed = speed, sprinting = sprinting }
end

local function loadSound(mode)
    local path = voices[mode].asset
    local resident = StaticFindObject(path)
    if valid(resident) then return resident end
    if not valid(assetHelpers) then
        assetHelpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
    end
    if not valid(assetHelpers) then
        return nil, "AssetRegistryHelpers is unavailable; cannot load the breathing sound."
    end
    -- UE4SS LoadAsset requires an AssetRegistry record, which custom containers
    -- may lack. The installed BPModLoader uses this direct UE4 FAssetData loader.
    local assetData = { ObjectPath = UEHelpers.FindOrAddFName(path) }
    local loaded = assetHelpers:GetAsset(assetData)
    if not valid(loaded) then
        return nil, "Direct " .. mode .. " sound load returned an invalid object: " .. path ..
            ". Check that the matching audio container is mounted."
    end
    if C.DebugLogging then log("Loaded " .. mode .. " sound asset: " .. loaded:GetFullName()) end
    return loaded
end

local function apply(pawn, mode, gain, mixerBlocked, freshAudio)
    local voice = voices[mode]
    if gain == 0 then stop(mode, pawn, freshAudio); return end
    if not valid(pawn) then stop(mode, pawn, freshAudio); return end
    local audio = freshAudio
    if voice.audioPath and not valid(audio) then lookupFailed(mode); return end
    if voice.lookupFailed and not voice.audioPath then return end
    -- An unresolved other voice may still be audible at its old gain. Only
    -- verified decreases/stops are safe until the whole mix is resolved again.
    if mixerBlocked and (not valid(audio) or gain > (voice.gain or 0)) then return end
    if not valid(audio) or not audio:IsPlaying() then
        stop(mode, pawn, audio)
        if voice.audioPath then return end
        if elapsed < voice.retryAt then return end
        local loadError
        local sound
        sound, loadError = loadSound(mode)
        if not valid(sound) then
            voice.retryAt = elapsed + 5
            errorLog(loadError or "Breathing sound is unavailable.")
            return
        end
        -- Create first and validate lookup before playback. A lookup failure
        -- cannot leave an audible orphan or cause repeated spawning each tick.
        audio = statics:CreateSound2D(pawn, sound, gain, C.Pitch, 0, nil, false, true)
        if not valid(audio) then
            voice.retryAt = elapsed + 5
            errorLog("CreateSound2D did not return a valid audio component.")
            return
        end
        local created = audio
        local ok, message = pcall(function()
            voice.audioFullName = created:GetFullName()
            voice.audioPath = voice.audioFullName:match("^%S+%s+(.+)$")
            voice.audioShortName = created:GetFName():ToString()
            voice.audioAddress = created:GetAddress()
            assert(voice.audioPath and voice.audioShortName and type(voice.audioAddress) == "number", "Audio component has no primitive identity")
            local owner = created:GetOuter()
            assert(valid(owner), "Audio component has no current owner")
            voice.ownerName, voice.ownerAddress, voice.ownerFullName = owner:GetFName():ToString(), owner:GetAddress(), owner:GetFullName()
            local level = owner:GetOuter()
            assert(valid(level), "Audio component owner has no current level")
            voice.levelAddress, voice.levelFullName = level:GetAddress(), level:GetFullName()
            if ModRef then
                ModRef:SetSharedVariable(voice.sharedKey, voice.audioPath)
                ModRef:SetSharedVariable(voice.sharedKey .. "Address", voice.audioAddress)
                ModRef:SetSharedVariable(voice.sharedKey .. "FullName", voice.audioFullName)
            end
            audio = resolveAudio(voice, pawn)
            assert(valid(audio), "New audio component cannot be freshly resolved")
            -- CreateSound2D defaults to UI audio; set native pause behavior
            -- before Play so even a missing setter fails without audible sound.
            audio:SetUISound(false)
            audio:Play(0.0)
            voice.gain = gain
        end)
        if not ok then
            -- Stop alone does not destroy an unplayed component. This wrapper
            -- was just returned by CreateSound2D in the current callback.
            local destroyed = pcall(function() created:K2_DestroyComponent(created) end)
            if destroyed then clearVoice(mode) end
            lookupFailed(mode)
            errorLog("Audio creation failed safely: " .. tostring(message))
            return
        end
        if not voice.lookupLogged then
            log("Voice ready: " .. mode .. " (lookup=" .. voice.lookupMethod .. ")")
            voice.lookupLogged = true
        end
        if C.DebugLogging then log("Playing " .. mode .. " breathing loop (lookup=" .. voice.lookupMethod .. ")") end
    end
    -- Manual ramp permits immediate reversal without a stale native fade-out stop.
    if voice.gain ~= gain then
        audio:SetVolumeMultiplier(gain)
        voice.gain = gain
    end
end

local function tick(pawnContext, step, localController)
    elapsed = elapsed + step
    local ok, message = pcall(function()
        if not initialized then
            -- UE4SS may reload edited Lua while its native audio voice survives.
            -- Retire only this mod's previous voice before creating a new one.
            -- Retire every old voice using only our two exact sound assets.
            -- Old releases may have lost paths for earlier duplicate loops.
            for _, audio in ipairs(FindAllOf("AudioComponent") or {}) do
                local sound = audio.Sound
                if valid(sound) then
                    local path = sound:GetFullName():match("^%S+%s+(.+)$")
                    if path == C.WalkSoundAsset or path == C.RunSoundAsset then audio:Stop() end
                end
            end
            if ModRef then
                local keys = { SINGLE_SHARED_AUDIO_KEY, voices.walk.sharedKey, voices.run.sharedKey }
                -- Discard the old pre-release pointer without dereferencing it.
                ModRef:SetSharedVariable(OLD_SHARED_AUDIO_KEY, nil)
                for _, key in ipairs(keys) do
                    ModRef:SetSharedVariable(key, nil)
                    ModRef:SetSharedVariable(key .. "Address", nil)
                    ModRef:SetSharedVariable(key .. "FullName", nil)
                end
            end
            initialized = true
        end
        local pawn, observation = observe(pawnContext, localController)
        if not valid(pawn) then
            stop(nil, pawnContext); State:reset(); setPawnName(nil)
            reportPhase(observation, State.gains, State.phase, nil)
            return
        end
        if observation.eligible and not gameplayTickLogged then
            log("Gameplay tick active: Eve ReceiveTick.")
            gameplayTickLogged = true
        end
        local gains, phase, mode = State:step(step, observation)
        local needsUpdate = phase ~= lastPhase or mode ~= lastMode
        reportPhase(observation, gains, phase, mode)
        for _, name in ipairs(MODES) do
            local voice = voices[name]
            if voice.lookupFailed or gains[name] ~= (voice.gain or 0) or (gains[name] > 0 and not voice.audioPath) then
                needsUpdate = true
            end
        end
        -- Steady voices need no lookup or native audio commands. Ownership is
        -- checked again for every gain/state change and lifecycle cleanup.
        if not needsUpdate then return end
        local freshVoices, mixerBlocked = {}, false
        for _, name in ipairs(MODES) do
            freshVoices[name] = resolveAudio(voices[name], pawn)
            if voices[name].audioPath and not valid(freshVoices[name]) then
                lookupFailed(name); mixerBlocked = true
            end
        end
        -- Update existing voices first, before spawning a destination voice.
        -- This keeps native combined volume capped during a crossfade.
        for _, name in ipairs(MODES) do
            local audio = freshVoices[name]
            if valid(audio) and gains[name] < (voices[name].gain or 0) then
                audio:SetVolumeMultiplier(gains[name])
                voices[name].gain = gains[name]
            end
        end
        for _, name in ipairs(MODES) do
            apply(pawn, name, gains[name], mixerBlocked, freshVoices[name])
            if voices[name].lookupFailed and voices[name].audioPath then mixerBlocked = true end
        end
    end)
    if not ok then
        stop(nil, pawnContext); State:reset()
        for _, mode in ipairs(MODES) do voices[mode].retryAt = elapsed + 5 end
        reportPhase({ eligible = false, speed = 0 }, State.gains, State.phase, nil)
        errorLog("Audio update failed safely: " .. tostring(message))
    end
end

-- Legacy ExecuteInGameThread drains its queue from arbitrary ProcessEvent calls,
-- including loading/Slate threads. Use the actual Eve actor tick instead.
local EVE_CLASS = "/Game/Art/Character/PC/CH_P_EVE_01/Blueprints/CH_P_EVE_01_Blueprint.CH_P_EVE_01_Blueprint_C"
local tickHooks, endHooks = nil, nil
local hooksRegistrationLogged = false
local tickElapsed = 0
local function actorTick(context, deltaSeconds)
    local ok, message = pcall(function()
        local step = type(deltaSeconds) == "number" and deltaSeconds or deltaSeconds:get()
        if type(step) ~= "number" or step < 0 then return end
        tickElapsed = tickElapsed + step
        if tickElapsed + 1e-9 < dt and step > 0 then return end
        local elapsedStep = tickElapsed
        tickElapsed = 0
        -- Frames between updates perform no UObject/controller observations.
        local pawn = context:get()
        local localController = nil
        if valid(pawn) then
            local controller = pawn.Controller
            if valid(controller) then
                if not controller:IsLocalPlayerController() then return end
                localController = controller
            end
        end
        tick(pawn, elapsedStep, localController)
    end)
    if not ok then errorLog("Eve tick callback failed: " .. tostring(message)) end
end
local function resetLifecycle(pawn)
    stop(nil, pawn); State:reset(); setPawnName(nil); tickElapsed = 0
    for _, mode in ipairs(MODES) do
        -- A failed, destroyed creation is safe to retry after a lifecycle change.
        -- An unresolved existing voice keeps its latch and identity.
        if not voices[mode].audioPath then voices[mode].lookupFailed = false end
    end
end
local function endPlay(context)
    local ok, message = pcall(function()
        resetLifecycle(context and context:get() or nil)
    end)
    if not ok then
        State:reset(); setPawnName(nil); tickElapsed = 0
        errorLog("Eve end-play cleanup failed safely: " .. tostring(message))
    end
end
local function registerActorHooks()
    if not tickHooks then
        local ok, pre, post = pcall(RegisterHook, EVE_CLASS .. ":ReceiveTick", actorTick)
        if ok and type(pre) == "number" and type(post) == "number" then tickHooks = { pre, post } end
    end
    if not endHooks then
        local ok, pre, post = pcall(RegisterHook, EVE_CLASS .. ":ReceiveEndPlay", endPlay)
        if ok and type(pre) == "number" and type(post) == "number" then endHooks = { pre, post } end
    end
    if tickHooks and endHooks and not hooksRegistrationLogged then
        log("Eve ReceiveTick/ReceiveEndPlay hooks registered.")
        hooksRegistrationLogged = true
    end
end
RegisterHook("/Script/Engine.PlayerController:ClientRestart", function(context)
    local ok, message = pcall(function()
        local controller = context and context:get() or nil
        resetLifecycle(valid(controller) and controller.Pawn or nil)
    end)
    if not ok then
        State:reset(); setPawnName(nil); tickElapsed = 0
        errorLog("Client restart cleanup failed safely: " .. tostring(message))
    end
    if tickHooks then pcall(UnregisterHook, EVE_CLASS .. ":ReceiveTick", tickHooks[1], tickHooks[2]); tickHooks = nil end
    if endHooks then pcall(UnregisterHook, EVE_CLASS .. ":ReceiveEndPlay", endHooks[1], endHooks[2]); endHooks = nil end
    registerActorHooks()
end)
-- Protected registration supports Lua reload while Eve's Blueprint is resident.
-- If it is not loaded yet, ClientRestart performs registration after possession.
registerActorHooks()
log("Loaded v0.2.9: Eve actor tick; walking/running breathing, louder sprint, " ..
    (C.IdleAfterMovement and "#2 idle only after movement." or
    ("one " .. tostring(C.FadeOutSeconds) .. "-second stop tail.")))
