"""Run the shipped Lua against UE API mocks with thread and native volume audits.

This checks logic/API shape; native audio decoding and listening remain in-game checks.
"""
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
from lupa.lua54 import LuaRuntime
checks = {}


def fixture(legacy=False, missing=None, debug=False, missing_helper=False, resident=False,
            blueprint_resident=True, nil_hook_ids=False, streaming=False, idle_after_movement=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('package.path = ' + json.dumps((ROOT / 'mod/Scripts/?.lua').as_posix()) + ' .. ";" .. package.path')
    lua.execute('''
      F={speed=0,grounded=true,paused=false,ignored=false,controllerValid=true,pawnValid=true,
         pawnName="CH_P_EVE_01_Blueprint_C /Game/Level.Eve_1",helperValid=true,onGameThread=false,
         spawns=0,creates=0,destroys=0,stops=0,loads=0,live=0,maximumLive=0,registryLoads=0,maximumGain=0,
         uobjectCalls=0,unsafeSchedules=0,callbackSerial=0,contextGets=0,controllerCalls=0,controllerAccesses=0,
         volumeSets=0,scans=0,hashFinds=0,staticAudioFinds=0,scopedStaticFinds=0,componentQueries=0,elementGets=0,ownerFinds=0,ownerAccesses=0,classFinds=0,worldGets=0,persistentAccesses=0,invalidIdentityNativeCalls=0,
         hooks={},hookRegistrations={},hookIds=0,
         activeHooks={},hookGenerations={},functionGeneration=1,blueprintResident=true,
         spawnCounts={walk=0,run=0},loadCounts={walk=0,run=0},assetValid={walk=true,run=true},
         resident={walk=false,run=false},gains={walk=0,run=0},volumes={},logs={},queue={},objects={},auditEnabled=true}
      F.paths={walk="/Game/CodexRunningBreath/Audio/SW_WalkBreathingLoop.SW_WalkBreathingLoop",
               run="/Game/CodexRunningBreath/Audio/SW_RunBreathingLoop.SW_RunBreathingLoop"}
      local function gt() assert(F.onGameThread,"UObject accessed off game thread");F.uobjectCalls=F.uobjectCalls+1 end
      local function audit()
        local gains={walk=0,run=0};local counts={walk=0,run=0};local live=0
        for _,a in pairs(F.objects) do
          if a.alive and a.playing and gains[a.mode]~=nil then gains[a.mode]=gains[a.mode]+a.gain;counts[a.mode]=counts[a.mode]+1;live=live+1 end
        end
        if F.auditEnabled then
          assert(counts.walk<=1 and counts.run<=1,"Duplicate native voice for a movement mode")
          assert(live<=2,"Too many native voices")
        end
        local total=gains.walk+gains.run
        if F.auditEnabled then assert(total>=0 and total<=.750000001,"Combined native volume exceeded the configured cap") end
        F.gains=gains;F.lastGain=total;F.maximumGain=math.max(F.maximumGain,total)
        F.maximumLive=math.max(F.maximumLive,live)
        table.insert(F.volumes,{walk=gains.walk,run=gains.run,total=total})
      end
      local sounds={}
      for _,mode in ipairs({"walk","run"}) do
        local m=mode;local s={mode=m};sounds[m]=s
        function s:IsValid() gt();return F.assetValid[m] end
        function s:GetFullName() gt();return "SoundWave "..F.paths[m] end
      end
      sounds.foreign={mode="foreign"}
      function sounds.foreign:IsValid() gt();return true end
      function sounds.foreign:GetFullName() gt();return "SoundWave /Game/Foreign/Ambience.Ambience" end
      F.sounds=sounds
      local helpers={};function helpers:IsValid() gt();return F.helperValid end
      function helpers:GetAsset(data)
        gt();local mode=nil
        for m,p in pairs(F.paths) do if data.ObjectPath==p then mode=m end end
        assert(mode,"Wrong sound ObjectPath passed to direct loader")
        F.loads=F.loads+1;F.loadCounts[mode]=F.loadCounts[mode]+1
        if F.assetValid[mode] then F.resident[mode]=true;return sounds[mode] end
        return nil
      end
      local movement={};function movement:IsValid() gt();return true end
      function movement:IsMovingOnGround() gt();if F.throwMovement then error("movement failure") end;return F.grounded end
      local pawn={};function pawn:IsValid() gt();return F.pawnValid end
      setmetatable(pawn,{__index=function(_,key)
        if key=="bSprint" then gt();if F.throwSprintFlag then error("Sprint flag unavailable") end;return F.sprintFlag end
        if key=="Controller" then gt();F.controllerAccesses=F.controllerAccesses+1;return F.controller end
      end})
      function pawn:GetFullName() gt();return F.pawnName end
      function pawn:GetVelocity() gt();return {X=F.speed,Y=0,Z=F.verticalSpeed or 0} end
      function pawn:GetMovementComponent() gt();return movement end
      function pawn:GetOuter() gt();return F.levelWrapper() end
      function pawn:GetWorld() gt();F.worldGets=F.worldGets+1;return F.worldWrapper() end
      local controller={Pawn=pawn};function controller:IsValid() gt();return F.controllerValid end
      function controller:IsMoveInputIgnored() gt();return F.ignored end
      function controller:IsLocalPlayerController() gt();F.controllerCalls=F.controllerCalls+1;return F.localPlayer~=false end
      F.controller=controller
      local statics={};function statics:IsValid() gt();return true end
      function statics:IsGamePaused(context) gt();return F.paused end
      function statics:SpawnSound2D(...) error("Audio must be validated before playback") end
      local audioWrapper
      F.audioLevel={alive=true,kind="level",address=7000,path="/Game/Art/BG/WorldMap/Dungeon_P/Matrix_XI.Matrix_XI:PersistentLevel"}
      function F.audioLevel:IsValid() gt();return self.alive end
      function F.audioLevel:GetFullName() gt();return "Level "..self.path end
      function F.audioLevel:GetAddress() gt();return self.address end
      setmetatable(F.audioLevel,{__index=function(_,key)
        if key=="WorldSettings" then gt();F.ownerAccesses=F.ownerAccesses+1;return not F.failOwnerAudio and audioWrapper(F.audioOuter) or nil end
      end})
      F.streamingLevel={alive=true,kind="streaming",address=7500,path="/Game/Art/BG/WorldMap/Dungeon_P/Matrix_XI_Sublevel.Matrix_XI_Sublevel:PersistentLevel"}
      function F.streamingLevel:IsValid() gt();return self.alive end
      function F.streamingLevel:GetFullName() gt();return "Level "..self.path end
      function F.streamingLevel:GetAddress() gt();return self.address end
      F.pawnOuter=F.audioLevel
      F.world={alive=true,kind="world",address=6000}
      function F.world:IsValid() gt();return F.worldValid~=false end
      function F.world:GetFullName() gt();return "World /Game/Art/BG/WorldMap/Dungeon_P/Matrix_XI.Matrix_XI" end
      function F.world:GetAddress() gt();return self.address end
      setmetatable(F.world,{__index=function(_,key)
        if key=="PersistentLevel" then gt();F.persistentAccesses=F.persistentAccesses+1;return not F.persistentMissing and audioWrapper(F.audioLevel) or nil end
      end})
      F.audioOuter={alive=true,kind="owner",address=8000,name="WorldSettings",level=F.audioLevel}
      function F.audioOuter:IsValid() gt();return self.alive end
      function F.audioOuter:GetFullName() gt();return "WorldSettings "..self.level.path.."."..self.name end
      function F.audioOuter:GetAddress() gt();return self.address end
      function F.audioOuter:GetOuter() gt();return audioWrapper(self.level) end
      function F.audioOuter:GetFName() gt();local name={};local text=self.name;function name:ToString() gt();return text end;return name end
      function F.audioOuter:GetComponentsByClass() error("GetComponentsByClass is not the reflected UE4.26 UFunction") end
      function F.audioOuter:K2_GetComponentsByClass(class)
        gt();assert(class==F.audioClass,"Native component query requires the rooted AudioComponent UClass")
        F.componentQueries=F.componentQueries+1
        local serial=F.callbackSerial
        local objects={}
        for _,object in pairs(F.objects) do
          if object.alive and object.owner==self and (not F.failScopedAudio or object.mode=="foreign") then table.insert(objects,object) end
        end
        table.sort(objects,function(a,b)
          if (a.mode=="foreign")~=(b.mode=="foreign") then return a.mode=="foreign" end
          return a.address<b.address
        end)
        local result={}
        for index,object in ipairs(objects) do
          local value=object
          result[index]={get=function()
            gt();assert(serial==F.callbackSerial,"Prior-callback array element reused")
            F.elementGets=F.elementGets+1
            return audioWrapper(value,true)
          end}
        end
        -- d3d1004 converts UFunction ArrayProperty returns into a one-based Lua
        -- table of RemoteUnrealParam elements, not property-access TArray userdata.
        return setmetatable(result,{__index=function(_,key)
          assert(serial==F.callbackSerial,"Prior-callback component array reused")
          if key=="ForEach" then error("UFunction array return has no TArray:ForEach method") end
        end})
      end
      F.ownerClass={};function F.ownerClass:IsValid() gt();return true end
      function F.ownerClass:GetFullName() gt();return "Class /Script/Engine.WorldSettings" end
      function F.ownerClass:GetAddress() gt();return 8500 end
      F.audioClass={};function F.audioClass:IsValid() gt();return true end
      function F.audioClass:GetFullName() gt();return "Class /Script/Engine.AudioComponent" end
      function F.audioClass:GetAddress() gt();return 9000 end
      audioWrapper=function(object,hashed)
        if not object or not object.alive then return nil end
        local serial=F.callbackSerial
        return setmetatable({}, {__index=function(_,key)
          assert(serial==F.callbackSerial,"Prior-callback audio wrapper reused")
          if key=="nativeAudio" then return object end
          if ((hashed and F.hashWrongAddress) or (object.kind=="owner" and F.ownerWrongAddress) or
              (object.kind=="level" and F.levelWrongAddress)) and key=="GetAddress" then
            return function() gt();return object.address+1 end
          end
          if ((hashed and F.hashWrongFullName) or (object.kind=="owner" and F.ownerWrongFullName) or
              (object.kind=="level" and F.levelWrongFullName)) and key=="GetFullName" then
            return function() gt();return "ForeignObject /Game/Foreign.ForeignObject" end
          end
          local member=object[key]
          if type(member)=="function" then
            return function(_, ...)
              assert(serial==F.callbackSerial,"Prior-callback audio wrapper reused")
              if hashed and (F.hashWrongAddress or F.hashWrongFullName) and
                  (key=="IsPlaying" or key=="SetUISound" or key=="SetVolumeMultiplier" or key=="Play" or key=="Stop") then
                F.invalidIdentityNativeCalls=F.invalidIdentityNativeCalls+1
                error("Native method called on an identity mismatch")
              end
              return member(object,...)
            end
          end
          return member
        end,__newindex=function(_,key,value)
          assert(serial==F.callbackSerial,"Prior-callback audio wrapper reused")
          object[key]=value
        end})
      end
      function F.levelWrapper() return audioWrapper(F.pawnOuter) end
      function F.worldWrapper() return not F.worldMissing and audioWrapper(F.world) or nil end
      function statics:CreateSound2D(context,asset,volume,pitch,start,concurrency,persist,autoDestroy)
        gt();assert(asset==sounds[asset.mode] and not persist and autoDestroy)
        F.creates=F.creates+1
        local owner=F.audioOuter
        local path=owner.level.path.."."..owner.name..".AudioComponent_"..(2147474739+F.creates)
        local a={kind="audio",owner=owner,mode=asset.mode,gain=volume,alive=true,playing=false,transient=true,Sound=asset,address=10000+F.creates}
        F.objects[path]=a;F.lastAudio=a;F.lastAudioPath=path
        function a:IsValid() gt();assert(self.alive,"Reclaimed audio wrapper dereferenced");return true end
        function a:GetFullName() gt();return "AudioComponent "..path end
        function a:GetAddress() gt();return self.address end
        function a:GetOuter() gt();if F.throwIdentityMethods then error("GetOuter unavailable") end;return audioWrapper(self.owner) end
        function a:GetClass() gt();if F.throwIdentityMethods then error("GetClass unavailable") end;return F.audioClass end
        function a:GetFName()
          gt();if F.throwIdentityMethods then error("GetFName unavailable") end
          local name={};function name:ToString() gt();return path:match("[^.:/]+$") end;return name
        end
        function a:IsPlaying() gt();return self.playing end
        function a:SetUISound(value) gt();if F.noUISound then error("SetUISound unavailable") end;self.uiSound=value end
        function a:SetVolumeMultiplier(v) gt();F.volumeSets=F.volumeSets+1;assert(v>=0 and v<=.750000001);self.gain=v;audit() end
        function a:Play(start)
          gt();assert(start==0 and self.uiSound==false,"Playback occurred before native pause setup")
          if not self.playing then
            if self.mode~="foreign" then F.spawns=F.spawns+1;F.spawnCounts[self.mode]=F.spawnCounts[self.mode]+1;F.live=F.live+1
            else F.foreignLive=(F.foreignLive or 0)+1 end
          end
          self.playing=true;audit()
        end
        function a:Stop()
          gt();if not self.playing then return end
          if self.alive then
            if self.mode~="foreign" then F.stops=F.stops+1;F.live=F.live-1 else F.foreignLive=F.foreignLive-1 end
          end
          self.playing=false;self.alive=false;self.gain=0;audit()
        end
        function a:K2_DestroyComponent(owner)
          gt();assert(owner==self or owner.nativeAudio==self);F.destroys=F.destroys+1
          if self.playing then self:Stop() end
          self.alive=false;self.gain=0;audit()
        end
        audit();return audioWrapper(a)
      end
      F.statics=statics
      package.preload.UEHelpers=function() return {
        GetPlayerController=function() error("Cached PlayerController helper must not be used") end,
        GetWorld=function() error("Cached World helper must not be used") end,
        GetPersistentLevel=function() error("Cached PersistentLevel helper must not be used") end,
        GetWorldSettings=function() error("Cached WorldSettings helper must not be used") end,
        GetGameplayStatics=function() gt();return statics end,
        FindOrAddFName=function(path) gt();return path end} end
      function LoadAsset(path) gt();F.registryLoads=F.registryLoads+1;return nil,false,false end
      function StaticFindObject(path,outer,name,exactClass)
        gt()
        if type(path)~="string" then
          assert(not F.rejectVoiceSearch,"Numeric-name StaticFindObject voice search is prohibited")
          assert(path~=nil and type(name)=="string" and exactClass==false,
            "Nil-class StaticFindObject calls are prohibited after the live crash")
          if path==F.ownerClass then
            assert(outer.nativeAudio==F.audioLevel and name==F.audioOuter.name,"WorldSettings lookup requires the fresh world's PersistentLevel")
            F.ownerFinds=F.ownerFinds+1
            return not F.failOwnerAudio and audioWrapper(F.audioOuter) or nil
          end
          assert(path==F.audioClass and outer.nativeAudio==F.audioOuter,"Audio lookup requires a fresh class-scoped WorldSettings result")
          F.scopedStaticFinds=F.scopedStaticFinds+1
          if F.unreliableNumericSearch and F.scopedStaticFinds>1 then return audioWrapper(F.lookupSibling) end
          local componentPath=F.audioOuter.level.path.."."..F.audioOuter.name.."."..name
          return not F.failScopedAudio and audioWrapper(F.objects[componentPath],true) or nil
        end
        if path=="/Script/Engine.WorldSettings" then F.classFinds=F.classFinds+1;return F.ownerClass end
        if path=="/Script/Engine.AudioComponent" then F.classFinds=F.classFinds+1;return F.audioClass end
        for mode,p in pairs(F.paths) do
          if path==p then return F.assetValid[mode] and F.resident[mode] and sounds[mode] or nil end
        end
        if path=="/Script/AssetRegistry.Default__AssetRegistryHelpers" then return F.helperValid and helpers or nil end
        F.staticAudioFinds=F.staticAudioFinds+1
        -- The live game fails full-path lookup for this WorldSettings-owned voice.
        return nil
      end
      function FindObject(class,outer,shortName,exactClass)
        gt();assert(class==nil and outer==-1 and type(shortName)=="string" and exactClass==false)
        F.hashFinds=F.hashFinds+1
        -- Reproduce the actual v0.2.5 diagnostic: the ANY_PACKAGE shortcut returns
        -- AudioComponent's UClass, rather than the requested native component.
        return F.audioClass
      end
      function FindAllOf(name)
        gt();assert(name=="AudioComponent");F.scans=(F.scans or 0)+1
        if F.failScanAudio then return nil end
        local result={};for _,object in pairs(F.objects) do if object.alive then table.insert(result,audioWrapper(object)) end end
        return result
      end
      ModRef={values={}}
      function ModRef:GetSharedVariable(key)
        gt();local value=self.values[key]
        assert(not (type(value)=="table" and value.transient),"Unsafe raw transient shared pointer read")
        return value
      end
      function ModRef:SetSharedVariable(key,value)
        gt();assert(not (type(value)=="table" and value.transient),"Unsafe raw transient shared pointer write")
        self.values[key]=value
      end
      function print(message) table.insert(F.logs,message) end
      function ExecuteInGameThread(callback) F.unsafeSchedules=F.unsafeSchedules+1;error("Unsafe ProcessEvent scheduler") end
      function LoopAsync(delay,callback) F.unsafeSchedules=F.unsafeSchedules+1;error("Async polling must not be used") end
      function LoopInGameThreadWithDelay(delay,callback) F.unsafeSchedules=F.unsafeSchedules+1;error("Actor lifecycle is required") end
      F.eveClass="/Game/Art/Character/PC/CH_P_EVE_01/Blueprints/CH_P_EVE_01_Blueprint.CH_P_EVE_01_Blueprint_C"
      function RegisterHook(path,callback)
        assert(path==F.eveClass..":ReceiveTick" or path==F.eveClass..":ReceiveEndPlay" or path=="/Script/Engine.PlayerController:ClientRestart")
        if path~= "/Script/Engine.PlayerController:ClientRestart" and not F.blueprintResident then error("Blueprint function is not resident") end
        F.hookRegistrations[path]=(F.hookRegistrations[path] or 0)+1
        if F.returnNilIds and path~= "/Script/Engine.PlayerController:ClientRestart" then return nil,nil end
        F.activeHooks[path]=(F.activeHooks[path] or 0)+1
        F.hookGenerations[path]=F.functionGeneration
        F.hooks[path]=callback;F.hookIds=F.hookIds+2
        return F.hookIds-1,F.hookIds
      end
      function UnregisterHook(path,pre,post)
        assert(type(pre)=="number" and type(post)=="number")
        F.activeHooks[path]=math.max(0,(F.activeHooks[path] or 0)-1);F.hooks[path]=nil
      end
      local context={};function context:get() gt();F.contextGets=F.contextGets+1;return pawn end
      local controllerContext={};function controllerContext:get() gt();return F.controller end
      local delta={};function delta:get() return F.actorDelta or .05 end
      function tick()
        F.callbackSerial=F.callbackSerial+1
        F.onGameThread=true
        if F.hookGenerations[F.eveClass..":ReceiveTick"]==F.functionGeneration then F.hooks[F.eveClass..":ReceiveTick"](context,delta) end
        F.onGameThread=false
      end
      function endPlay() F.callbackSerial=F.callbackSerial+1;F.onGameThread=true;F.hooks[F.eveClass..":ReceiveEndPlay"](context);F.onGameThread=false end
      function clientRestart() F.callbackSerial=F.callbackSerial+1;F.onGameThread=true;F.hooks["/Script/Engine.PlayerController:ClientRestart"](controllerContext);F.onGameThread=false end
      function ticks(n) for i=1,n do tick() end end
      function logsContain(needle)
        for _,message in ipairs(F.logs) do if message:find(needle,1,true) then return true end end
        return false
      end
      function logCount(needle)
        local count=0;for _,message in ipairs(F.logs) do if message:find(needle,1,true) then count=count+1 end end;return count
      end
      function audibleGain()
        local gain=0
        for _,a in pairs(F.objects) do if a.alive and a.playing and a.mode~="foreign" and (not F.paused or a.uiSound) then gain=gain+a.gain end end
        return gain
      end
    ''')
    if legacy:
        lua.execute('LoopInGameThreadWithDelay=nil')
    if missing:
        lua.execute('F.assetValid[' + json.dumps(missing) + ']=false')
    if missing_helper:
        lua.execute('F.helperValid=false')
    if resident:
        lua.execute('F.resident.walk=true;F.resident.run=true')
    if debug:
        lua.execute('require("config").DebugLogging=true')
    if not blueprint_resident:
        lua.execute('F.blueprintResident=false')
    if nil_hook_ids:
        lua.execute('F.returnNilIds=true')
    if streaming:
        lua.execute('F.pawnOuter=F.streamingLevel')
    if idle_after_movement is not None:
        lua.execute('require("config").IdleAfterMovement=' + ('true' if idle_after_movement else 'false'))
    for name in ('config.lua', 'running_state.lua', 'main.lua'):
        lua.execute('assert(load(' + json.dumps((ROOT / 'mod/Scripts' / name).read_text()) + '))')
    lua.execute((ROOT / 'mod/Scripts/main.lua').read_text())
    return lua


def check(name, lua, expression):
    value = bool(lua.eval(expression))
    checks[name] = value
    assert value, name


for legacy in (False, True):
    label = 'legacy' if legacy else 'modern'
    l = fixture(legacy, idle_after_movement=False)
    l.execute('ticks(1200)')
    check(label + '_cold_idle_never_creates_audio', l, 'F.creates==0 and F.spawns==0')
    l.execute('F.speed=120;ticks(2);F.speed=0;ticks(1200)')
    check(label + '_brief_movement_does_not_arm_a_stop_tail', l, 'F.spawns==0')
    l.execute('F.speed=120;ticks(20)')
    check(label + '_walking_uses_clip_two', l, 'F.spawnCounts.walk==1 and F.spawnCounts.run==0 and math.abs(F.gains.walk-.45)<1e-8')
    l.execute('F.speed=500;ticks(2);F.speed=120;ticks(4)')
    check(label + '_brief_run_spike_does_not_create_clip_three', l, 'F.spawnCounts.run==0 and F.spawnCounts.walk==1')
    l.execute('F.speed=500;ticks(5)')
    check(label + '_walk_to_run_crossfade_is_volume_capped', l, 'F.live==2 and F.gains.walk>0 and F.gains.run>0 and math.abs(F.lastGain-.45)<1e-8')
    l.execute('ticks(20);F.speed=260;ticks(5)')
    check(label + '_steady_run_and_hysteresis_use_clip_three', l, 'F.live==1 and math.abs(F.gains.run-.45)<1e-8')
    l.execute('F.speed=750;ticks(10);F.speed=650;ticks(10)')
    check(label + '_sprint_volume_and_hysteresis', l, 'F.spawnCounts.run==1 and math.abs(F.gains.run-.75)<1e-8')
    l.execute('F.speed=550;ticks(10)')
    check(label + '_leaving_sprint_reuses_running_voice', l, 'F.spawnCounts.run==1 and math.abs(F.gains.run-.45)<1e-8')
    l.execute('F.speed=0;tick();ticks(15)')
    check(label + '_stopping_running_switches_to_clip_two', l, 'F.live==1 and F.gains.run==0 and F.gains.walk>0 and F.gains.walk<.45')
    l.execute('ticks(24)')
    check(label + '_stop_tail_alive_just_before_two_seconds', l, 'F.live==1 and math.abs(F.gains.walk-.01125)<1e-8')
    l.execute('tick();F.stopTailSpawns=F.spawns')
    check(label + '_stop_tail_silent_at_exactly_two_seconds', l, 'F.live==0 and F.lastGain==0')
    l.execute('ticks(1800)')
    check(label + '_held_still_never_rearms_tail', l, 'F.live==0 and F.spawns==F.stopTailSpawns')
    l.execute('F.speed=120;ticks(20);F.grounded=false;tick()')
    check(label + '_airborne_stops_immediately', l, 'F.live==0 and F.lastGain==0')
    l.execute('F.grounded=true;ticks(20);F.paused=true;tick()')
    check(label + '_observed_pause_stops_immediately', l, 'F.live==0')
    l.execute('F.paused=false;ticks(20);F.ignored=true;tick()')
    check(label + '_ignored_input_stops_immediately', l, 'F.live==0')
    l.execute('F.ignored=false;ticks(20);require("config").Enabled=false;tick()')
    check(label + '_disabled_stops_immediately', l, 'F.live==0')
    l.execute('require("config").Enabled=true;ticks(20);F.controllerValid=false;tick()')
    check(label + '_lost_controller_stops_without_cached_wrapper', l, 'F.live==0 and not logsContain("Cached PlayerController")')
    l.execute('F.controllerValid=true;ticks(20);F.pawnName="CH_P_TACHY_01_Blueprint_C Tachy";tick()')
    check(label + '_non_eve_silent', l, 'F.live==0')
    l.execute('F.pawnName="CH_P_EVE_01_Blueprint_C Eve_2";ticks(20);F.throwMovement=true;tick()')
    check(label + '_native_api_failure_stops_owned_voices', l, 'F.live==0')
    check(label + '_native_volume_and_voice_audits', l, 'F.maximumGain<=.750000001 and F.maximumLive<=2')
    check(label + '_actor_lifecycle_only_uobject_access', l, 'F.uobjectCalls>0 and F.unsafeSchedules==0')

l = fixture(idle_after_movement=False)
l.execute('F.speed=120;ticks(20);F.speed=0;tick();ticks(20)')
check('walking_stop_tail_half_volume_after_one_second', l, 'F.spawnCounts.walk==1 and F.live==1 and math.abs(F.gains.walk-.225)<1e-8')
l.execute('F.speed=120;ticks(12)')
check('resuming_walk_cancels_tail_and_reuses_existing_voice', l, 'F.spawnCounts.walk==1 and F.stops==0 and math.abs(F.gains.walk-.45)<1e-8')
l.execute('F.speed=0;tick();ticks(40)')
check('qualified_new_movement_arms_one_new_two_second_tail', l, 'F.live==0 and F.spawnCounts.walk==1')

l = fixture()
l.execute('F.speed=120;ticks(20);F.speed=500;ticks(10);F.beforeWalk=F.spawnCounts.walk;F.beforeRun=F.spawnCounts.run;F.speed=0;tick();ticks(1);F.speed=500;ticks(20)')
check('stop_during_crossfade_then_resume_reuses_both_voices', l, 'F.spawnCounts.walk==F.beforeWalk and F.spawnCounts.run==F.beforeRun and F.live==1 and math.abs(F.gains.run-.45)<1e-8')
l = fixture()
l.execute('F.sprintFlag=true;F.speed=500;ticks(30);F.speed=0;tick();ticks(15)')
check('stopping_sprint_selects_clip_two_without_sprint_volume', l, 'F.live==1 and F.gains.run==0 and F.gains.walk>0 and F.gains.walk<=.45')

l = fixture(idle_after_movement=False)
l.execute('S=require("running_state").new(require("config"));S:step(.15,{eligible=true,speed=120});S:step(.5,{eligible=true,speed=120});S:step(.05,{eligible=true,speed=0});S:step(1,{eligible=true,speed=0});S:step(.999,{eligible=true,speed=0})')
check('irregular_dt_tail_remains_alive_until_two_seconds', l, 'S.phase=="stop_fading" and S.gains.walk>0')
l.execute('S:step(.001,{eligible=true,speed=0});S:step(600,{eligible=true,speed=0})')
check('irregular_dt_tail_expires_once_at_two_seconds', l, 'S.phase=="silent" and S.gains.walk==0 and S.gains.run==0 and S.mode==nil')
l.execute('S:step(.15,{eligible=true,speed=500,sprinting=true});S:step(1,{eligible=true,speed=500,sprinting=true});S:step(.01,{eligible=true,speed=0});S:step(3,{eligible=true,speed=0})')
check('one_long_elapsed_tick_does_not_extend_stop_tail', l, 'S.phase=="silent" and S.gains.walk==0 and S.gains.run==0')

l = fixture(idle_after_movement=False)
l.execute('F.failStaticAudio=true;F.speed=120;ticks(20);F.speed=500;ticks(30);F.speed=0;tick();ticks(600)')
check('fresh_owned_component_lookup_preserves_single_voice_per_mode', l, 'F.spawnCounts.walk==2 and F.spawnCounts.run==1 and F.live==0 and F.maximumLive<=2 and F.scans==1')
l = fixture()
l.execute('F.failScopedAudio=true;F.failScanAudio=true;F.speed=120;ticks(200)')
check('failed_new_lookup_is_destroyed_before_play_and_never_recreated', l, 'F.creates==1 and F.spawns==0 and F.live==0 and F.destroys==1 and logsContain("replacement is blocked")')
l = fixture(idle_after_movement=False)
l.execute('F.speed=120;ticks(20);F.beforeCreates=F.creates;F.failScopedAudio=true;F.failScanAudio=true;ticks(100);F.speed=0;tick();ticks(700);F.speed=120;ticks(100)')
check('later_ambiguous_lookup_loss_cannot_stack_replacements', l, 'F.creates==F.beforeCreates and F.spawns==1 and logsContain("replacement is blocked") and type(ModRef.values.CodexRunningBreathActiveAudioPathWalk)=="string"')
l.execute('F.failScopedAudio=false;F.failScanAudio=false;F.speed=0;tick();ticks(40)')
check('retained_identity_can_be_resolved_and_stopped_later', l, 'F.live==0 and ModRef.values.CodexRunningBreathActiveAudioPathWalk==nil')
l = fixture()
l.execute('F.sprintFlag=true;F.speed=500;ticks(30);F.beforeCreates=F.creates;F.failScopedAudio=true;F.failScanAudio=true;F.speed=0;tick();ticks(10)')
check('unresolved_sprint_voice_blocks_new_walking_tail_and_volume_increase', l, 'F.creates==F.beforeCreates and F.spawnCounts.walk==0 and F.gains.run==.75 and F.maximumGain<=.750000001')
l.execute('F.failScopedAudio=false;F.failScanAudio=false;ticks(20)')
check('resolved_sprint_identity_recovers_into_single_walking_tail', l, 'F.live==1 and F.gains.run==0 and F.gains.walk>0 and F.spawnCounts.walk==1 and F.maximumGain<=.750000001')
l = fixture()
l.execute('F.speed=120;ticks(20);F.beforeCreates=F.creates;F.failScopedAudio=true;F.failScanAudio=true;F.sprintFlag=true;F.speed=500;ticks(40)')
check('unresolved_walk_voice_blocks_new_sprint_voice', l, 'F.creates==F.beforeCreates and F.spawnCounts.run==0 and math.abs(F.gains.walk-.45)<1e-8')
l.execute('F.failScopedAudio=false;F.failScanAudio=false;ticks(20)')
check('resolved_walk_identity_recovers_into_single_louder_running_voice', l, 'F.live==1 and F.gains.walk==0 and math.abs(F.gains.run-.75)<1e-8 and F.spawnCounts.run==1 and F.maximumGain<=.750000001')
l = fixture()
l.execute('F.noUISound=true;F.speed=120;ticks(100)')
check('missing_pause_setter_destroys_unplayed_creation', l, 'F.spawns==0 and F.creates==1 and F.live==0 and F.destroys==1 and logsContain("Audio creation failed safely")')
l = fixture()
l.execute('F.speed=120;ticks(20)')
check('shared_identity_is_primitive_path_address_and_fullname', l, 'type(ModRef.values.CodexRunningBreathActiveAudioPathWalk)=="string" and type(ModRef.values.CodexRunningBreathActiveAudioPathWalkAddress)=="number" and type(ModRef.values.CodexRunningBreathActiveAudioPathWalkFullName)=="string"')

l = fixture()
l.execute('F.auditEnabled=false;F.onGameThread=true;for _,mode in ipairs({"walk","walk","run","foreign"}) do local a=F.statics:CreateSound2D({},F.sounds[mode],.45,1,0,nil,false,true);a:SetUISound(false);a:Play(0);if mode=="foreign" then F.foreignAudio=a.nativeAudio end end;F.onGameThread=false;ticks(1);F.auditEnabled=true')
check('migration_retires_three_owned_orphans_but_preserves_foreign_audio', l, 'F.stops==3 and F.live==0 and F.foreignLive==1 and F.foreignAudio.alive and F.foreignAudio.playing')
l.execute('F.speed=120;ticks(20)')
check('migration_cleanup_runs_once_before_new_audio', l, 'F.live==1 and F.foreignLive==1 and F.stops==3')
l = fixture()
l.execute('F.speed=500;ticks(30);F.speed=0;tick();ticks(5);F.beforeSpawns=F.spawns;F.beforeStops=F.stops')
l.execute((ROOT / 'mod/Scripts/main.lua').read_text())
l.execute('F.speed=120;ticks(20)')
check('reload_retires_both_native_voices_before_new_movement_audio', l, 'F.spawns==F.beforeSpawns+1 and F.stops==F.beforeStops+2 and F.live==1')
l = fixture()
l.execute('ModRef.values.CodexRunningBreathActiveAudio={transient=true,alive=false};tick()')
check('obsolete_raw_shared_pointer_cleared_without_read', l, 'ModRef.values.CodexRunningBreathActiveAudio==nil')

l = fixture()
l.execute('F.actorDelta=.01;F.speed=120;ticks(4)')
check('actor_elapsed_accumulator_throttles_updates', l, 'F.creates==0')
l.execute('ticks(61)')
check('actor_elapsed_accumulator_uses_game_time_for_start_fade', l, 'F.spawns==1 and math.abs(F.gains.walk-.45)<1e-8')
check('scheduler_uses_no_async_or_process_event_actions', l, 'F.unsafeSchedules==0 and #F.queue==0 and F.activeHooks[F.eveClass..":ReceiveTick"]==1')
l.execute('F.paused=true')
check('pause_without_actor_tick_is_silent_through_native_pause_flag', l, 'F.lastAudio.uiSound==false and audibleGain()==0 and F.live==1')
l.execute('F.paused=false;ticks(100)')
check('native_pause_resume_keeps_same_walking_voice', l, 'F.spawnCounts.walk==1 and F.live==1')
l = fixture()
l.execute('F.localPlayer=false;F.speed=500;ticks(30)')
check('nonlocal_eve_cannot_start_audio', l, 'F.creates==0')
l.execute('F.localPlayer=true;F.speed=120;ticks(20);F.localPlayer=false;ticks(20)')
check('nonlocal_eve_does_not_interrupt_local_voice', l, 'F.live==1 and F.spawnCounts.walk==1')
l.execute('F.localPlayer=true;F.controller=nil;tick()')
check('fresh_controller_loss_cleans_audio_without_helper_cache', l, 'F.live==0 and not logsContain("Cached PlayerController")')

l = fixture()
l.execute('F.speed=500;ticks(30);F.speed=0;tick();ticks(5);endPlay()')
check('endplay_clears_both_native_voices_before_gc', l, 'F.live==0 and ModRef.values.CodexRunningBreathActiveAudioPathWalk==nil and ModRef.values.CodexRunningBreathActiveAudioPathRun==nil')
l.execute('F.pawnValid=false;endPlay();F.pawnValid=true;ticks(20)')
check('endplay_does_not_depend_on_pending_kill_pawn_validity', l, 'F.live==0')
l.execute('F.speed=120;ticks(20);F.registrationsBefore=F.hookRegistrations[F.eveClass..":ReceiveTick"];clientRestart();clientRestart();ticks(20)')
check('repeated_clientrestart_rebinds_without_duplicate_callbacks', l, 'F.hookRegistrations[F.eveClass..":ReceiveTick"]==F.registrationsBefore+2 and F.activeHooks[F.eveClass..":ReceiveTick"]==1 and F.activeHooks[F.eveClass..":ReceiveEndPlay"]==1 and F.live==1')
l.execute('F.functionGeneration=F.functionGeneration+1;endPlay();clientRestart();ticks(20)')
check('clientrestart_rebinds_recreated_blueprint', l, 'F.hookGenerations[F.eveClass..":ReceiveTick"]==F.functionGeneration and F.live==1')
check('sanity_logs_do_not_repeat_every_tick', l, 'logCount("hooks registered.")==1 and logCount("Gameplay tick active")==1')
l = fixture(blueprint_resident=False)
check('unloaded_blueprint_hooks_are_deferred', l, 'not logsContain("hooks registered.")')
l.execute('F.blueprintResident=true;clientRestart();F.speed=120;ticks(20)')
check('clientrestart_binds_loaded_blueprint', l, 'F.activeHooks[F.eveClass..":ReceiveTick"]==1 and F.live==1')
l = fixture(nil_hook_ids=True)
check('nil_hook_ids_do_not_claim_success', l, 'not logsContain("hooks registered.")')
l.execute('F.returnNilIds=false;clientRestart();F.speed=120;ticks(20)')
check('nil_hook_ids_are_retryable', l, 'F.hookRegistrations[F.eveClass..":ReceiveTick"]==2 and F.live==1')

l = fixture()
l.execute('F.sprintFlag=true;F.speed=500;ticks(30)')
check('native_true_sprint_flag_boosts_at_normal_run_speed', l, 'math.abs(F.gains.run-.75)<1e-8')
l.execute('F.sprintFlag=false;F.speed=900;ticks(10)')
check('native_false_sprint_flag_overrides_speed_fallback', l, 'math.abs(F.gains.run-.45)<1e-8 and F.spawnCounts.run==1')
l = fixture()
l.execute('F.throwSprintFlag=true;F.speed=750;ticks(30)')
check('unreadable_sprint_flag_uses_speed_fallback', l, 'math.abs(F.gains.run-.75)<1e-8')
l = fixture()
l.execute('F.sprintFlag=false;require("config").UseSprintFlag=false;F.speed=750;ticks(30)')
check('sprint_flag_can_be_disabled', l, 'math.abs(F.gains.run-.75)<1e-8')
l = fixture()
l.execute('F.pawnName="CH_P_EVE_01_Blueprint_C /Game/Lobby/Lobby.LOBBY:PersistentLevel.Eve";ticks(20);F.speed=500;ticks(20)')
check('lobby_eve_stays_silent_at_idle_and_run_speed', l, 'F.creates==0')
l.execute('F.pawnName="CH_P_EVE_01_Blueprint_C /Temp/Untitled_0.Untitled:PersistentLevel.Eve";ticks(20)')
check('startup_temp_eve_stays_silent', l, 'F.creates==0')
l = fixture()
l.execute('F.verticalSpeed=1000;ticks(20)')
check('vertical_speed_does_not_trigger_audio', l, 'F.creates==0')
l = fixture()
l.execute('F.speed=500;ticks(30)')
check('custom_sound_loads_directly_without_asset_registry_lookup', l, 'F.loadCounts.run==1 and F.registryLoads==0 and F.spawnCounts.run==1')
l = fixture(resident=True)
l.execute('F.speed=120;ticks(20);F.speed=500;ticks(20)')
check('resident_custom_assets_do_not_reload', l, 'F.loads==0 and F.registryLoads==0 and F.spawnCounts.walk==1 and F.spawnCounts.run==1')
for missing, available, speed, available_speed in [('walk','run',120,500), ('run','walk',500,120)]:
    l = fixture(missing=missing)
    l.execute(f'F.speed={speed};ticks(40)')
    check('missing_' + missing + '_asset_is_silent_and_throttled', l, f'F.spawnCounts.{missing}==0 and F.loadCounts.{missing}==1')
    l.execute('ticks(80)')
    check('missing_' + missing + '_asset_retries_after_five_seconds', l, f'F.loadCounts.{missing}==2 and F.spawnCounts.{missing}==0')
    l.execute(f'F.speed={available_speed};ticks(40)')
    check('missing_' + missing + '_does_not_disable_' + available, l, f'F.live==1 and math.abs(F.gains.{available}-.45)<1e-8')
l = fixture(missing_helper=True)
l.execute('F.speed=120;ticks(40)')
check('missing_loader_helper_reports_specific_error', l, 'F.spawns==0 and F.loads==0 and logsContain("AssetRegistryHelpers is unavailable")')
l = fixture(missing='run')
l.execute('F.speed=500;ticks(40)')
check('invalid_direct_loader_reports_exact_run_path', l, 'logsContain("Direct run sound load returned an invalid object: "..F.paths.run)')
l = fixture(debug=True, idle_after_movement=False)
l.execute('ticks(20);F.idleLogs=#F.logs;ticks(100)')
check('debug_silent_idle_does_not_log_each_poll', l, '#F.logs==F.idleLogs')
l.execute('F.speed=120;ticks(20);F.walkLogs=#F.logs;ticks(100)')
check('debug_walking_does_not_log_each_poll', l, '#F.logs==F.walkLogs')
l.execute('F.speed=500;ticks(30);F.speed=750;ticks(20);F.speed=0;tick();ticks(600)')
check('debug_reports_movement_sprint_stop_tail_and_stop', l, 'logsContain("State walking") and logsContain("State running") and logsContain("State sprinting") and logsContain("State stop_fading") and logsContain("Stopped walk breathing loop")')
l.execute('F.controllerValid=false;tick();F.nilLogs=#F.logs;ticks(20)')
check('debug_missing_pawn_logs_once', l, '#F.logs==F.nilLogs and logsContain("Pawn: <none>")')

# Performance checks count native work and enforce wrapper lifetime, rather than
# timing mocked calls or assuming an engine frame rate. Every audio lookup returns
# a callback-bound wrapper that errors if the shipped Lua caches it across ticks.
l = fixture()
l.execute('F.failStaticAudio=true;F.speed=120;ticks(20);F.beforeScans=F.scans;F.beforeSets=F.volumeSets;F.beforeHashes=F.componentQueries;F.beforeStatic=F.staticAudioFinds;ticks(600)')
check('stable_walk_needs_no_audio_lookup_with_primitive_gain_unchanged', l,
      'F.scans==F.beforeScans and F.componentQueries==F.beforeHashes and F.hashFinds==0 and F.staticAudioFinds==F.beforeStatic and F.spawnCounts.walk==1 and F.live==1')
check('stable_walk_has_no_redundant_native_volume_setters', l,
      'F.volumeSets==F.beforeSets and math.abs(F.gains.walk-.45)<1e-8')
l.execute('F.speed=500;ticks(30);F.beforeScans=F.scans;F.beforeSets=F.volumeSets;F.beforeScoped=F.componentQueries;ticks(600)')
check('stable_run_has_no_audio_lookups_scans_or_redundant_volume_setters', l,
      'F.componentQueries==F.beforeScoped and F.scans==F.beforeScans and F.volumeSets==F.beforeSets and F.spawnCounts.run==1 and F.live==1 and math.abs(F.gains.run-.45)<1e-8')
l.execute('F.sprintFlag=true;ticks(20);F.beforeSets=F.volumeSets;F.beforeScoped=F.componentQueries;ticks(600)')
check('stable_sprint_volume_remains_louder_without_native_setter_spam', l,
      'F.componentQueries==F.beforeScoped and F.volumeSets==F.beforeSets and F.spawnCounts.run==1 and math.abs(F.gains.run-.75)<1e-8')
check('audio_wrappers_are_resolved_fresh_for_every_gain_change', l,
      'F.componentQueries>20 and F.ownerAccesses==F.componentQueries and F.scopedStaticFinds==0 and F.ownerFinds==0 and F.unsafeSchedules==0 and F.maximumGain<=.750000001')

l = fixture()
l.execute('F.speed=120;ticks(20);F.beforeScans=F.scans;F.beforeClasses=F.classFinds;ticks(200)')
check('owned_component_lookup_caches_only_rooted_native_class', l,
      'F.classFinds==1 and F.classFinds==F.beforeClasses and F.hashFinds==0 and F.staticAudioFinds==0 and F.scopedStaticFinds==0 and F.ownerFinds==0 and F.scans==F.beforeScans and F.spawnCounts.walk==1 and F.live==1')

for mismatch in ('Address', 'FullName'):
    l = fixture()
    l.execute(f'F.failStaticAudio=true;F.failScanAudio=true;F.hashWrong{mismatch}=true;F.speed=120;ticks(100)')
    check('owned_component_lookup_rejects_wrong_' + mismatch.lower() + '_before_native_playback', l,
          'F.componentQueries>0 and F.invalidIdentityNativeCalls==0 and F.creates==1 and F.destroys==1 and F.spawns==0 and F.live==0')

l = fixture()
l.execute('F.actorDelta=.005;F.speed=120;ticks(9)')
check('actor_gate_precedes_all_pawn_and_controller_access', l,
      'F.controllerCalls==0 and F.controllerAccesses==0 and F.contextGets==0 and F.uobjectCalls==0')
l.execute('ticks(191)')
check('two_hundred_actor_frames_do_only_twenty_controller_checks', l,
      'F.controllerCalls==20 and F.controllerAccesses==20 and F.contextGets==20 and F.spawnCounts.walk==1 and math.abs(F.gains.walk-.45)<1e-8')

l = fixture(idle_after_movement=False)
l.execute('F.speed=120;ticks(20);F.speed=0;tick();F.beforeSets=F.volumeSets;ticks(20)')
check('stop_tail_each_decrease_sets_native_volume_once', l,
      'F.volumeSets==F.beforeSets+20 and F.live==1 and F.gains.walk>0 and F.gains.walk<.45')
l = fixture()
l.execute('F.speed=120;ticks(20);F.beforeScans=F.scans;F.beforeCreates=F.creates;F.failScopedAudio=true;F.speed=500;ticks(200)')
check('unresolved_voice_never_triggers_repeated_global_scans', l,
      'F.scans==F.beforeScans and F.creates==F.beforeCreates and F.spawnCounts.walk==1 and F.maximumGain<=.750000001')

l = fixture()
l.execute('F.speed=120;ticks(20);F.speed=500;ticks(30)')
check('normal_logging_reports_each_voice_ready_once_with_owned_component_lookup', l,
      'logCount("Voice ready: walk (lookup=owner-components)")==1 and logCount("Voice ready: run (lookup=owner-components)")==1 and not logsContain("Playing walk breathing loop")')
l.execute('endPlay();F.speed=120;ticks(20);clientRestart();F.speed=500;ticks(30);F.speed=0;ticks(620);F.speed=120;ticks(20)')
check('voice_readiness_logging_does_not_repeat_after_stop_endplay_or_restart', l,
      'logCount("Voice ready:")==2 and F.spawnCounts.walk>=3 and F.spawnCounts.run==2')
l = fixture()
l.execute('F.speed=120;ticks(20)')
check('normal_logging_reports_only_the_live_verified_lookup_method', l,
      'logCount("Voice ready: walk (lookup=owner-components)")==1 and not logsContain("lookup=short-name") and not logsContain("lookup=full-path") and not logsContain("lookup=class/outer/name")')

l = fixture()
l.execute('F.speed=120;ticks(20)')
check('live_worldsettings_outer_and_large_native_fname_resolve_before_play', l,
      'F.spawnCounts.walk==1 and F.lastAudioPath==F.audioLevel.path..".WorldSettings.AudioComponent_2147474740" and F.ownerAccesses==F.componentQueries and F.scopedStaticFinds==0 and F.ownerFinds==0 and F.hashFinds==0 and F.staticAudioFinds==0 and F.lastAudio.uiSound==false')
for scope in ('owner', 'level'):
    for mismatch in ('Address', 'FullName'):
        l = fixture()
        l.execute(f'F.speed=120;ticks(20);F.beforeAudioFinds=F.componentQueries;F.beforeOwnerAccesses=F.ownerAccesses;F.beforeCreates=F.creates;F.{scope}Wrong{mismatch}=true;F.sprintFlag=true;F.speed=500;ticks(20)')
        check(scope + '_identity_rejects_wrong_' + mismatch.lower() + '_before_audio_lookup', l,
              'F.componentQueries==F.beforeAudioFinds and F.creates==F.beforeCreates and F.spawnCounts.run==0 and F.live==1 and math.abs(F.gains.walk-.45)<1e-8 and F.maximumGain<=.750000001' +
              (' and F.ownerAccesses==F.beforeOwnerAccesses' if scope == 'level' else ' and F.ownerAccesses>F.beforeOwnerAccesses'))
        l.execute(f'F.{scope}Wrong{mismatch}=false;ticks(20)')
        check(scope + '_identity_recovery_' + mismatch.lower() + '_restores_one_sprint_voice', l,
              'F.live==1 and F.spawnCounts.run==1 and math.abs(F.gains.run-.75)<1e-8 and F.maximumGain<=.750000001')
l.execute('F.beforeAudioFinds=F.componentQueries;F.beforeOwnerAccesses=F.ownerAccesses;F.beforeSets=F.volumeSets;ticks(200)')
check('successful_identity_recovery_clears_latch_and_restores_steady_skip', l,
      'F.componentQueries==F.beforeAudioFinds and F.ownerAccesses==F.beforeOwnerAccesses and F.volumeSets==F.beforeSets and F.live==1 and math.abs(F.gains.run-.75)<1e-8')
l = fixture()
l.execute('F.speed=120;ticks(20);F.pawnValid=false;endPlay()')
check('pending_kill_endplay_resolves_and_stops_an_active_voice_before_gc', l,
      'F.live==0 and F.stops==1 and ModRef.values.CodexRunningBreathActiveAudioPathWalk==nil and not logsContain("cleanup failed")')
l = fixture()
l.execute('F.speed=120;ticks(20);F.speed=500;ticks(5);assert(F.live==2);clientRestart()')
check('clientrestart_fresh_controller_pawn_stops_both_crossfade_voices', l,
      'F.live==0 and F.stops==2 and ModRef.values.CodexRunningBreathActiveAudioPathWalk==nil and ModRef.values.CodexRunningBreathActiveAudioPathRun==nil and not logsContain("cleanup failed")')

l = fixture(streaming=True, idle_after_movement=False)
l.execute('assert(F.pawnOuter~=F.audioLevel);F.speed=120;ticks(20);F.speed=500;ticks(30);F.sprintFlag=true;ticks(20)')
check('streaming_pawn_resolves_audio_owned_by_world_persistent_level', l,
      'F.live==1 and F.spawnCounts.walk==1 and F.spawnCounts.run==1 and math.abs(F.gains.run-.75)<1e-8 and F.worldGets>0 and F.persistentAccesses>0 and F.ownerAccesses>0 and F.ownerFinds==0 and F.hashFinds==0 and F.staticAudioFinds==0')
l.execute('F.pawnOuter=F.audioLevel;F.sprintFlag=false;ticks(20)')
check('pawn_level_change_in_same_world_reuses_the_owned_audio_voice', l,
      'F.live==1 and F.spawnCounts.run==1 and math.abs(F.gains.run-.45)<1e-8 and not logsContain("replacement is blocked")')
l.execute('F.pawnOuter=F.streamingLevel;F.speed=0;tick();ticks(39)')
check('streaming_world_stop_tail_remains_alive_at_one_point_nine_five_seconds', l,
      'F.live==1 and F.gains.walk>0 and F.gains.run==0')
l.execute('tick();F.beforeSpawns=F.spawns;ticks(600)')
check('streaming_world_stop_tail_ends_at_two_seconds_and_idle_never_rearms', l,
      'F.live==0 and F.lastGain==0 and F.spawns==F.beforeSpawns')
l = fixture(streaming=True)
l.execute('F.speed=500;ticks(30);F.pawnValid=false;endPlay()')
check('streaming_pending_kill_endplay_uses_fresh_world_for_cleanup', l,
      'F.live==0 and F.stops==1 and ModRef.values.CodexRunningBreathActiveAudioPathRun==nil and not logsContain("cleanup failed")')

for missing_stage, toggle, reason in (
        ('world', 'worldMissing', 'world: invalid current World'),
        ('persistent_level', 'persistentMissing', 'level: invalid result'),
        ('worldsettings', 'failOwnerAudio', 'WorldSettings owner: invalid result')):
    l = fixture(streaming=True)
    l.execute(f'F.speed=120;ticks(20);F.beforeAudioFinds=F.componentQueries;F.beforeOwnerAccesses=F.ownerAccesses;F.beforePersistentAccesses=F.persistentAccesses;F.{toggle}=true;F.speed=500;ticks(30)')
    check('missing_' + missing_stage + '_blocks_creation_and_logs_existing_identity_reason_once', l,
          'F.componentQueries==F.beforeAudioFinds and F.creates==1 and F.spawnCounts.run==0 and F.live==1 and F.gains.walk==.45 and F.maximumGain<=.750000001 and logCount("Lookup failure walk:")==1 and logsContain(' + json.dumps(reason) + ')' +
          (' and F.ownerAccesses==F.beforeOwnerAccesses and F.persistentAccesses==F.beforePersistentAccesses' if missing_stage == 'world' else
           ' and F.ownerAccesses==F.beforeOwnerAccesses' if missing_stage == 'persistent_level' else ''))
    l.execute(f'F.{toggle}=false;ticks(20);F.beforeAudioFinds=F.componentQueries;F.beforeWorldGets=F.worldGets;ticks(200)')
    check('restored_' + missing_stage + '_recovers_owned_voice_and_zero_query_steady_state', l,
          'F.live==1 and F.spawnCounts.run==1 and F.gains.run==.45 and F.componentQueries==F.beforeAudioFinds and F.worldGets==F.beforeWorldGets')

l = fixture(streaming=True)
l.execute('F.onGameThread=true;F.foreignComponents={};for i=1,3 do local a=F.statics:CreateSound2D({},F.sounds.foreign,.10,1,0,nil,false,true);a:SetUISound(false);a:Play(0);F.foreignComponents[i]=a.nativeAudio end;F.onGameThread=false;F.lookupSibling=F.foreignComponents[1];F.unreliableNumericSearch=true;F.rejectVoiceSearch=true;F.speed=120;ticks(20)')
check('native_owned_table_remote_elements_select_exact_voice_among_numeric_siblings', l,
      'F.spawnCounts.walk==1 and F.live==1 and F.foreignLive==3 and math.abs(F.gains.walk-.45)<1e-8 and F.elementGets>F.componentQueries and F.scopedStaticFinds==0 and F.hashFinds==0 and F.staticAudioFinds==0 and not logsContain("replacement is blocked")')
l.execute('F.beforeQueries=F.componentQueries;F.beforeElements=F.elementGets;F.beforeSets=F.volumeSets;ticks(600)')
check('steady_owned_voice_with_foreign_siblings_enumerates_no_components', l,
      'F.componentQueries==F.beforeQueries and F.elementGets==F.beforeElements and F.volumeSets==F.beforeSets and F.live==1 and F.foreignLive==3')
l.execute('F.speed=500;ticks(30);F.sprintFlag=true;ticks(20)')
check('sprint_crossfade_preserves_unrelated_worldsettings_audio_components', l,
      'F.live==1 and F.spawnCounts.walk==1 and F.spawnCounts.run==1 and math.abs(F.gains.run-.75)<1e-8 and F.foreignLive==3 and F.foreignComponents[1].alive and F.foreignComponents[1].playing and F.foreignComponents[1].gain==.10 and F.foreignComponents[2].gain==.10 and F.foreignComponents[3].gain==.10 and F.maximumGain<=.750000001')
l.execute('F.speed=0;tick();ticks(40);endPlay()')
check('owned_tail_and_lifecycle_stop_leave_all_foreign_numeric_siblings_playing', l,
      'F.live==0 and F.foreignLive==3 and F.foreignComponents[1].alive and F.foreignComponents[1].playing and F.foreignComponents[2].alive and F.foreignComponents[2].playing and F.foreignComponents[3].alive and F.foreignComponents[3].playing and F.scopedStaticFinds==0 and F.hashFinds==0 and F.staticAudioFinds==0')

# The idle option is armed by the same confirmed movement gate as playback.
# Keep these tests on the actual default, alongside the original opt-out tail
# checks above, so a config regression cannot silently change the release.
l = fixture()
check('armed_idle_is_enabled_by_shipped_default', l,
      'require("config").IdleAfterMovement==true and require("config").FadeOutSeconds==2')
l.execute('ticks(12000)')
check('armed_idle_world_startup_stays_silent_for_ten_minutes', l,
      'F.creates==0 and F.spawns==0 and F.live==0 and F.volumeSets==0 and F.componentQueries==0')
l.execute('F.speed=49;ticks(300);F.speed=0;ticks(1200)')
check('under_threshold_movement_does_not_arm_idle', l,
      'F.creates==0 and F.spawns==0 and F.live==0')

for mode, speed in (('walk', 120), ('run', 500)):
    l = fixture()
    l.execute(f'F.speed={speed};ticks(2);F.speed=0;ticks(1200)')
    check('unconfirmed_' + mode + '_does_not_arm_idle', l,
          'F.creates==0 and F.spawns==0 and F.live==0 and F.componentQueries==0')

l = fixture()
l.execute('F.speed=120;ticks(3);F.speed=0;ticks(20);F.idleAudio=F.lastAudio;F.beforeCreates=F.creates;ticks(1200)')
check('exact_start_hold_brief_walk_settles_to_full_idle_gain', l,
      'F.spawnCounts.walk==1 and F.spawnCounts.run==0 and F.live==1 and math.abs(F.gains.walk-.45)<1e-8 and F.lastAudio==F.idleAudio and F.creates==F.beforeCreates')

for movement, speed, sprinting in (('walk', 120, False), ('run', 500, False), ('sprint', 500, True)):
    l = fixture()
    l.execute(f'F.speed={speed};F.sprintFlag={str(sprinting).lower()};ticks(30);F.movementGain=F.lastGain;F.speed=0;tick();F.firstStopGain=F.lastGain;ticks(19);F.idleAudio=F.lastAudio')
    check('confirmed_' + movement + '_stop_settles_to_one_walk_idle_voice', l,
          'F.live==1 and F.spawnCounts.walk==1 and F.spawnCounts.run==' + ('0' if movement == 'walk' else '1') +
          ' and math.abs(F.gains.walk-.45)<1e-8 and F.gains.run==0 and F.lastAudio.mode=="walk" and F.maximumGain<=.750000001')
    check(movement + '_stop_crossfade_has_no_silence_or_cap_excess', l,
          'F.firstStopGain>0 and F.firstStopGain<=.750000001 and math.abs(F.movementGain-' + ('.75' if sprinting else '.45') + ')<1e-8')
    l.execute('F.beforeCreates=F.creates;F.beforeSpawns=F.spawns;F.beforeStops=F.stops;F.beforeQueries=F.componentQueries;F.beforeElements=F.elementGets;F.beforeSets=F.volumeSets;ticks(12000)')
    check(movement + '_armed_idle_keeps_same_voice_for_ten_minutes', l,
          'F.live==1 and F.lastAudio==F.idleAudio and F.creates==F.beforeCreates and F.spawns==F.beforeSpawns and F.stops==F.beforeStops and math.abs(F.gains.walk-.45)<1e-8 and F.gains.run==0 and logCount("Voice ready: walk (lookup=owner-components)")==1')
    check(movement + '_steady_armed_idle_has_zero_native_lookup_and_gain_work', l,
          'F.componentQueries==F.beforeQueries and F.elementGets==F.beforeElements and F.volumeSets==F.beforeSets and F.maximumGain<=.750000001')
    l.execute('F.speed=120;F.sprintFlag=false;ticks(20);F.speed=0;ticks(20)')
    check(movement + '_armed_idle_to_walk_and_back_reuses_voice_without_gain_changes', l,
          'F.live==1 and F.lastAudio==F.idleAudio and F.creates==F.beforeCreates and F.spawns==F.beforeSpawns and F.stops==F.beforeStops and F.volumeSets==F.beforeSets and math.abs(F.gains.walk-.45)<1e-8')

l = fixture()
l.execute('F.speed=120;ticks(20);F.speed=0;ticks(20);F.idleAudio=F.lastAudio;F.beforeSets=F.volumeSets;F.beforeQueries=F.componentQueries;for i=1,20 do F.speed=120;ticks(3);F.speed=0;ticks(2) end')
check('rapid_confirmed_walk_idle_cycles_do_not_restart_or_change_gain', l,
      'F.live==1 and F.lastAudio==F.idleAudio and F.spawnCounts.walk==1 and F.spawnCounts.run==0 and F.stops==0 and F.volumeSets==F.beforeSets and math.abs(F.gains.walk-.45)<1e-8 and F.maximumGain<=.750000001')

l = fixture()
l.execute('S=require("running_state").new(require("config"));for i=1,3 do S:step(.05,{eligible=true,speed=120}) end;S:step(.05,{eligible=true,speed=0});S:step(600,{eligible=true,speed=0})')
check('pure_state_armed_idle_has_walk_mode_and_idle_phase_indefinitely', l,
      'S.phase=="idle" and S.mode=="walk" and S.idling and not S.moving and not S.stopping and math.abs(S.gains.walk-.45)<1e-8 and S.gains.run==0')
l.execute('S:reset();S:step(600,{eligible=true,speed=0})')
check('pure_state_reset_clears_idle_arm', l,
      'S.phase=="silent" and S.mode==nil and not S.idling and S.gains.walk==0 and S.gains.run==0')

# Observe each existing lifecycle/input rejection while idle, then require fresh
# confirmed movement after it clears. Pending-kill/EndPlay models pawn death;
# this intentionally makes no claim of a new health-property detector.
for rejection, enter, leave in (
        ('paused_tick', 'F.paused=true;tick()', 'F.paused=false'),
        ('ignored_input', 'F.ignored=true;tick()', 'F.ignored=false'),
        ('airborne', 'F.grounded=false;tick()', 'F.grounded=true'),
        ('disabled_config', 'require("config").Enabled=false;tick()', 'require("config").Enabled=true'),
        ('invalid_controller', 'F.controllerValid=false;tick()', 'F.controllerValid=true'),
        ('invalid_pawn', 'F.pawnValid=false;tick()', 'F.pawnValid=true'),
        ('lobby_menu', 'F.pawnName="CH_P_EVE_01_Blueprint_C /Game/Lobby/Lobby.LOBBY:PersistentLevel.Eve";tick()', 'F.pawnName="CH_P_EVE_01_Blueprint_C /Game/Level.Eve_1"'),
        ('temporary_world', 'F.pawnName="CH_P_EVE_01_Blueprint_C /Temp/Untitled_0.Untitled:PersistentLevel.Eve";tick()', 'F.pawnName="CH_P_EVE_01_Blueprint_C /Game/Level.Eve_1"'),
        ('changed_pawn', 'F.pawnName="CH_P_EVE_01_Blueprint_C /Game/Level.Eve_2";tick()', ''),
        ('pending_kill_endplay', 'F.pawnValid=false;endPlay()', 'F.pawnValid=true'),
        ('client_restart', 'clientRestart()', '')):
    l = fixture()
    l.execute('F.speed=120;ticks(20);F.speed=0;ticks(20)')
    l.execute(enter)
    check('armed_idle_' + rejection + '_stops_existing_voice', l,
          'F.live==0 and F.stops==1 and F.gains.walk==0 and F.gains.run==0')
    l.execute(leave + ';F.beforeCreates=F.creates;F.beforeSpawns=F.spawns;ticks(600)')
    check('armed_idle_' + rejection + '_remains_disarmed_after_recovery', l,
          'F.live==0 and F.creates==F.beforeCreates and F.spawns==F.beforeSpawns')
    l.execute('F.speed=120;ticks(20);F.speed=0;ticks(20)')
    check('armed_idle_' + rejection + '_rearms_only_after_new_confirmed_movement', l,
          'F.live==1 and F.spawnCounts.walk==2 and F.spawnCounts.run==0 and math.abs(F.gains.walk-.45)<1e-8 and F.maximumGain<=.750000001')

l = fixture()
l.execute('F.speed=120;ticks(20);F.speed=0;ticks(20);F.oldIdleAudio=F.lastAudio')
l.execute((ROOT / 'mod/Scripts/main.lua').read_text())
l.execute('F.beforeCreates=F.creates;ticks(600)')
check('lua_reload_retires_armed_idle_and_restarts_with_silent_state', l,
      'not F.oldIdleAudio.alive and F.live==0 and F.creates==F.beforeCreates and F.spawnCounts.walk==1')
l.execute('F.speed=120;ticks(20);F.speed=0;ticks(20)')
check('lua_reload_idle_rearms_after_new_movement_without_orphan_voice', l,
      'F.live==1 and F.spawnCounts.walk==2 and math.abs(F.gains.walk-.45)<1e-8 and F.maximumLive<=2')

l = fixture(idle_after_movement=False)
l.execute('require("config").IdleAfterMovement=nil;F.speed=120;ticks(20);F.speed=0;tick();ticks(39)')
check('legacy_missing_idle_option_retains_two_second_stop_tail', l,
      'F.live==1 and F.gains.walk>0 and F.gains.run==0')
l.execute('tick();F.beforeCreates=F.creates;ticks(600)')
check('legacy_missing_idle_option_ends_tail_and_stays_silent', l,
      'F.live==0 and F.lastGain==0 and F.creates==F.beforeCreates')

report = {'passed': all(checks.values()), 'lua_version': 'Lua 5.4', 'checks': checks,
          'source_sha256': {name: hashlib.sha256((ROOT / 'mod/Scripts' / name).read_bytes()).hexdigest()
                            for name in ('config.lua', 'main.lua', 'running_state.lua')},
          'scope': 'Actual shipped Lua executed with mocked UE APIs, game-thread assertions and per-native-call volume/voice audits. No in-game audio verification.',
          'runtime_verified': False}
(ROOT / 'checks/lua-behavior-tests.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
