-- Movement selects clips; idle playback is armed only by confirmed movement.
local M = {}
function M.new(config)
    local state = {}
    function state:reset()
        self.weights = { walk = 0, run = 0 }
        self.gains = { walk = 0, run = 0 }
        self.mode, self.pending, self.held, self.phase = nil, nil, 0, "silent"
        self.moving, self.stopping, self.idling, self.now = false, false, false, 0
        self.stopStartedAt, self.tailEnvelope, self.envelope = nil, 1, 1
        self.sprinting, self.runVolume = false, config.Volume
    end
    state:reset()
    function state:step(dt, observation)
        if not observation.eligible then
            self:reset()
            return self.gains, self.phase, self.mode
        end
        self.now = self.now + dt
        local speed = observation.speed
        local threshold = self.moving and config.WalkStopSpeedCmPerSecond or config.WalkStartSpeedCmPerSecond
        local isMoving = speed >= threshold
        local candidate = nil
        if isMoving then
            candidate = (speed >= config.RunStartSpeedCmPerSecond or
                (self.moving and self.mode == "run" and speed >= config.RunStopSpeedCmPerSecond)) and "run" or "walk"
            if self.moving and candidate == self.mode then
                self.pending, self.held = nil, 0
            else
                if self.pending == candidate then self.held = self.held + dt
                else self.pending, self.held = candidate, dt end
                if self.held + 1e-9 >= config.StartHoldSeconds then
                    self.mode, self.pending, self.held = candidate, nil, 0
                    self.moving, self.stopping, self.idling, self.stopStartedAt = true, false, false, nil
                end
            end
        else
            self.pending, self.held = nil, 0
            if self.moving then
                -- Only a completed movement episode can enter idle. Held-still
                -- samples keep the same voice and never start another episode.
                self.moving, self.mode = false, "walk"
                if config.IdleAfterMovement then
                    self.idling, self.stopping, self.stopStartedAt = true, false, nil
                else
                    self.idling, self.stopping, self.stopStartedAt = false, true, self.now
                    local sum = self.weights.walk + self.weights.run
                    self.tailEnvelope = self.envelope * sum
                    if sum > 0 then
                        self.weights.walk, self.weights.run = self.weights.walk / sum, self.weights.run / sum
                    end
                end
            end
        end
        if self.stopping then
            local duration = config.FadeOutSeconds
            local tailTime = self.now - self.stopStartedAt
            if duration <= 0 or tailTime + 1e-9 >= duration then
                self:reset()
                return self.gains, self.phase, self.mode
            end
            self.envelope = self.tailEnvelope * math.max(0, 1 - tailTime / duration)
        elseif self.moving or self.idling then
            local rise = config.FadeInSeconds > 0 and dt / config.FadeInSeconds or 1
            self.envelope = math.min(1, self.envelope + rise)
        end
        if not self.mode then return self.gains, self.phase, self.mode end
        local sprintThreshold = self.sprinting and config.SprintStopSpeedCmPerSecond or config.SprintStartSpeedCmPerSecond
        local wantsSprint = speed >= sprintThreshold
        if observation.sprinting ~= nil then wantsSprint = observation.sprinting end
        self.sprinting = self.moving and self.mode == "run" and candidate == "run" and wantsSprint
        local targetVolume = self.sprinting and config.SprintVolume or config.Volume
        local volumeStep = config.SprintFadeSeconds > 0 and
            (config.SprintVolume - config.Volume) * dt / config.SprintFadeSeconds or
            (config.SprintVolume - config.Volume)
        if targetVolume > self.runVolume then
            self.runVolume = math.min(targetVolume, self.runVolume + volumeStep)
        elseif targetVolume < self.runVolume then
            self.runVolume = math.max(targetVolume, self.runVolume - volumeStep)
        end
        local other = self.mode == "run" and "walk" or "run"
        local duration = self.weights[other] > 0 and config.CrossfadeSeconds or config.FadeInSeconds
        local blendStep = duration > 0 and dt / duration or 1
        self.weights[other] = math.max(0, self.weights[other] - blendStep)
        self.weights[self.mode] = math.min(1 - self.weights[other], self.weights[self.mode] + blendStep)
        for _, mode in ipairs({ "walk", "run" }) do
            if self.weights[mode] < 1e-8 then self.weights[mode] = 0 end
        end
        self.gains.walk = self.weights.walk * config.Volume * self.envelope
        self.gains.run = self.weights.run * self.runVolume * self.envelope
        if self.stopping then self.phase = "stop_fading"
        elseif self.weights.walk > 0 and self.weights.run > 0 then self.phase = "crossfading"
        elseif self.idling then self.phase = "idle"
        elseif self.mode == "run" then self.phase = self.sprinting and "sprinting" or "running"
        else self.phase = "walking" end
        return self.gains, self.phase, self.mode
    end
    return state
end
return M
