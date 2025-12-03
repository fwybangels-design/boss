-- Chat promotion script (teleport restart improvements)
-- This is your earlier fixed script with improved post-teleport auto-restart logic.
-- Behavior changes:
-- 1) Before teleport, script attempts several known "queue" methods (queue_on_teleport, syn.queue_on_teleport, fluxus.queue_on_teleport).
-- 2) If no queue function is available, it will attempt to copy a small loader string to the clipboard and notify you so you can paste/run it after the hop.
-- 3) Notifications/logs explain whether the loader was queued successfully or whether manual re-injection is required.
-- Note: automatic persistence across teleports relies on your executor supporting queue_on_teleport. If it does not, manual paste/run after hop is required.

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")
local TextChatService = game:GetService("TextChatService")
local UserInputService = game:GetService("UserInputService")
local StarterGui = game:GetService("StarterGui")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TeleportService = game:GetService("TeleportService")

-- UI library load (original)
local uiLib = loadstring(game:HttpGet('https://sirius.menu/rayfield'))()

local window = uiLib:CreateWindow({
    Name = "chat promotion script",
    Theme = "Default",
    ToggleUIKeybind = "K",
    KeySystem = true,
    KeySettings = {
        Title = "Chat Promotion Key",
        Subtitle = "dm gio https://t.me/giobleh",
        Note = "If you want to use the script contact gio on tele",
        FileName = "Key",
        SaveKey = true,
        GrabKeyFromSite = true,
        Key = {"https://pastebin.com/raw/0Wqtqma1"}
    }
})

local tabHome = window:CreateTab("Home")
local sectionMain = tabHome:CreateSection("Main")

local localPlayer = Players.LocalPlayer

local settingsFilename = "chatpromotion_settings.json"

local spamServer = ""
local autoHopEnabled = false
local maxPerServer = 5
local followConnection = nil

local cannedMessages = {
    "ageplayer heaven in /kingdamon",
    "cnc and ageplay in vcs /kingdamon",
    "ageplayers and regressers /kingdamon dc",
    "her little parts are out /kingdamon",
    "join for combosses /kingdamon dc",
    "camgir1s in /kingdamon jvc",
    "yo jvc rn she going crazy /kingdamon",
    "YO WHAT ARE THEY DOING ON CAM /kingdamon",
    "$$$ GWS IN /kingdamon JOIN UP",
    "tight ageplayers in /kingdamon jvc"
}

-- Save/load settings
local function saveSettings()
    local data = { spamServer = spamServer, autoHopEnabled = autoHopEnabled }
    if writefile then
        pcall(function()
            writefile(settingsFilename, HttpService:JSONEncode(data))
        end)
    end
end

local function loadSettings()
    if isfile and isfile(settingsFilename) then
        local ok, content = pcall(function() return readfile(settingsFilename) end)
        if ok and content then
            local ok2, decoded = pcall(function() return HttpService:JSONDecode(content) end)
            if ok2 and decoded then
                spamServer = decoded.spamServer or "/kingdamon"
                autoHopEnabled = decoded.autoHopEnabled or false
            end
        end
    end
end

loadSettings()

-- Best-effort fast flags and rendering tweaks
local function applyFastFlags()
    local flags = {
        DFIntTaskSchedulerTargetFps = 20,
        FFlagDebugDisableInGameMenuV2 = true,
        FFlagDisableInGameMenuV2 = true,
        DFIntTextureQualityOverride = 1,
        FFlagRenderNoLights = true,
        FFlagRenderNoShadows = true,
        DFIntDebugFRMQualityLevelOverride = 1,
        DFFlagTextureQualityOverrideEnabled = true,
        FFlagHandleAltEnterFullscreenManually = false,
        DFIntConnectionMTUSize = 1200,
        DFIntMaxMissedWorldStepsRemembered = 1,
        DFIntDefaultTimeoutTimeMs = 3000,
        FFlagDebugSimIntegrationStabilityTesting = false,
        DFFlagDebugRenderForceTechnologyVoxel = true,
        FFlagUserHandleCameraToggle = false
    }
    for name, val in pairs(flags) do
        pcall(function() game:SetFastFlag(name, val) end)
    end
end

local function applySettingsTweaks()
    pcall(function()
        settings().Network.IncomingReplicationLag = 0
        settings().Network.RenderStreamedRegions = false
        settings().Rendering.QualityLevel = 1
        settings().Rendering.MeshPartDetailLevel = Enum.MeshPartDetailLevel.Level01
        settings().Rendering.MaterialQualityLevel = Enum.MaterialQualityLevel.Level01
        settings().Physics.AllowSleep = true
        settings().Physics.PhysicsEnvironmentalThrottle = Enum.EnvironmentalPhysicsThrottle.DefaultAuto
    end)
end

-- UI hide while running
local function hideGuiLoop()
    spawn(function()
        while autoHopEnabled do
            pcall(function()
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.EmotesMenu, false)
                StarterGui:SetCore("TopbarEnabled", false)
            end)
            pcall(function()
                local pg = localPlayer:FindFirstChild("PlayerGui")
                if pg then
                    for _, child in pairs(pg:GetChildren()) do
                        if child:IsA("ScreenGui") and child.Name ~= "Chat" then
                            child.Enabled = false
                        end
                    end
                end
            end)
            pcall(function() if workspace.CurrentCamera then workspace.CurrentCamera.FieldOfView = 30 end end)
            wait(1)
        end
    end)
end

-- Ensure new chat UI available
local function ensureChatEnabledLoop()
    spawn(function()
        while autoHopEnabled do
            pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, true) end)
            pcall(function()
                local pg = localPlayer:FindFirstChild("PlayerGui")
                if pg then
                    local chatGui = pg:FindFirstChild("Chat")
                    if chatGui then chatGui.Enabled = true end
                end
            end)
            pcall(function() if TextChatService.ChatInputBarConfiguration then TextChatService.ChatInputBarConfiguration.Enabled = true end end)
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then break end
            wait(0.5)
        end
    end)
end

-- Performance loop
local function performanceLoop()
    spawn(function()
        while autoHopEnabled do
            pcall(function()
                for _, obj in pairs(workspace:GetDescendants()) do
                    if obj:IsA("Decal") or obj:IsA("Texture") then obj.Transparency = 1 end
                    if obj:IsA("ParticleEmitter") or obj:IsA("Smoke") or obj:IsA("Sparkles") or obj:IsA("Fire") then obj.Enabled = false end
                    if obj:IsA("Sound") then obj.Volume = 0 end
                end
            end)
            wait(1)
        end
    end)
end

-- Get public servers with pagination (returns list of instance ids)
local function getAvailableServers(placeId, maxPages)
    maxPages = maxPages or 5
    local results = {}
    local cursor = nil

    for page = 1, maxPages do
        local url = "https://games.roblox.com/v1/games/" .. tostring(placeId) .. "/servers/Public?sortOrder=Asc&limit=100"
        if cursor and cursor ~= "" then
            url = url .. "&cursor=" .. tostring(cursor)
        end

        local ok, body = pcall(function()
            return game:HttpGet(url, true)
        end)

        if not ok then
            warn(("getAvailableServers: HttpGet failed on page %d: %s"):format(page, tostring(body)))
            break
        end

        local decoded
        local decOk, decErr = pcall(function() decoded = HttpService:JSONDecode(body) end)
        if not decOk or type(decoded) ~= "table" then
            warn(("getAvailableServers: JSON decode failed on page %d; body len=%d"):format(page, #tostring(body)))
            break
        end

        local list = decoded.data or {}
        print(("getAvailableServers page %d: returned %d entries, nextPageCursor='%s'"):format(page, #list, tostring(decoded.nextPageCursor)))
        for _, server in ipairs(list) do
            if server and server.id and server.playing and server.maxPlayers and server.playing < server.maxPlayers and server.id ~= game.JobId then
                table.insert(results, server.id)
            end
        end

        cursor = decoded.nextPageCursor
        if not cursor or cursor == "" then break end
        wait(0.2)
    end

    print(("getAvailableServers: found %d candidate servers for place %s"):format(#results, tostring(placeId)))
    return results
end

-- Helper: build the loader string that will be queued for post-teleport execution.
-- Update the URL below if you want to point to a different hosted script.
local function build_loader_string()
    local loader_url = "https://raw.githubusercontent.com/fwybangels-design/boss/refs/heads/main/imabosss_obscured.lua"
    local loader = ([[wait(1)
pcall(function() loadstring(game:HttpGet("%s"))() end)]]):format(loader_url)
    return loader
end

-- Try to queue the loader using common executor queue functions.
-- Returns true if queued successfully, false otherwise. Also returns a message.
local function try_queue_loader(loader_str)
    -- 1) global queue_on_teleport
    if type(queue_on_teleport) == "function" then
        local ok, err = pcall(function() queue_on_teleport(loader_str) end)
        if ok then return true, "queued via global queue_on_teleport" end
    end

    -- 2) syn (Synapse X)
    if syn and type(syn.queue_on_teleport) == "function" then
        local ok, err = pcall(function() syn.queue_on_teleport(loader_str) end)
        if ok then return true, "queued via syn.queue_on_teleport" end
    end

    -- 3) fluxus
    if fluxus and type(fluxus.queue_on_teleport) == "function" then
        local ok, err = pcall(function() fluxus.queue_on_teleport(loader_str) end)
        if ok then return true, "queued via fluxus.queue_on_teleport" end
    end

    -- 4) krnl (krnl has a different name in some builds) - best-effort probing
    if cloaked and type(cloaked.queue_on_teleport) == "function" then
        local ok, err = pcall(function() cloaked.queue_on_teleport(loader_str) end)
        if ok then return true, "queued via cloaked.queue_on_teleport" end
    end

    -- Not queued by known functions
    return false, "no known queue_on_teleport available"
end

-- Teleport to another server, try multiple candidates and fallbacks; queue script if possible
local function teleportToAnotherServer()
    print("teleportToAnotherServer: gathering servers for place:", tostring(game.PlaceId), "current job:", tostring(game.JobId))

    local servers = getAvailableServers(game.PlaceId, 6)
    if not servers or #servers == 0 then
        print("teleportToAnotherServer: No available servers found from API; attempting fallback Teleport to place (random instance).")
        local ok, err = pcall(function() TeleportService:Teleport(game.PlaceId) end)
        if not ok then
            warn("teleportToAnotherServer: fallback Teleport failed:", err)
            wait(6)
            return teleportToAnotherServer()
        end
        return
    end

    -- Build loader and attempt to queue it
    local loader_str = build_loader_string()
    local queued, qmsg = try_queue_loader(loader_str)
    if queued then
        print("teleportToAnotherServer: loader queued successfully:", qmsg)
        uiLib:Notify({ Title = "Queued Loader", Content = "Script loader has been queued for post-teleport execution ("..qmsg..")", Duration = 5 })
    else
        print("teleportToAnotherServer: could NOT queue loader automatically:", qmsg)
        -- Attempt to copy loader to clipboard so you can paste it on the new server if needed
        local clipboard_done = false
        if setclipboard then
            pcall(function() setclipboard(loader_str) clipboard_done = true end)
        elseif syn and syn.set_clipboard then
            pcall(function() syn.set_clipboard(loader_str) clipboard_done = true end)
        elseif set_clipboard then
            pcall(function() set_clipboard(loader_str) clipboard_done = true end)
        end

        if clipboard_done then
            uiLib:Notify({ Title = "Manual Restart", Content = "No queue available: loader string copied to clipboard. Paste & run it after teleport.", Duration = 8 })
            print("teleportToAnotherServer: loader copied to clipboard; paste & run after the hop if needed.")
        else
            uiLib:Notify({ Title = "Manual Restart Required", Content = "No queue available and clipboard unavailable. You will need to re-inject the script after teleport.", Duration = 10 })
            print("teleportToAnotherServer: no automatic queue available and clipboard failed; manual re-injection required.")
        end
    end

    -- Try up to N random candidates
    local tries = math.min(5, #servers)
    for i = 1, tries do
        local idx = math.random(1, #servers)
        local instanceId = servers[idx]
        print(("teleportToAnotherServer: trying instance %s (attempt %d/%d)"):format(instanceId, i, tries))

        -- Try TeleportToPlaceInstance variants (executor-dependent)
        local okTele, teleErr = pcall(function()
            -- try 3-arg with player (some environments accept this)
            pcall(function() TeleportService:TeleportToPlaceInstance(game.PlaceId, instanceId, Players.LocalPlayer) end)
            -- try 2-arg fallback
            TeleportService:TeleportToPlaceInstance(game.PlaceId, instanceId)
        end)

        if okTele then
            print("teleportToAnotherServer: Teleport issued to instance:", instanceId)
            return
        else
            warn("teleportToAnotherServer: Teleport attempt failed for instance:", instanceId, "err:", teleErr)
            -- remove tried instance and try another
            table.remove(servers, idx)
        end
        wait(1)
    end

    -- All chosen instances failed — fallback to random Teleport
    warn("teleportToAnotherServer: all chosen instances failed, attempting fallback Teleport to place.")
    pcall(function() TeleportService:Teleport(game.PlaceId) end)
end

-- Build messages with server replacement
local function buildMessageList(serverStr)
    local serverBase = serverStr ~= "" and serverStr or "/kingdamon"
    local out = {}
    for i, msg in ipairs(cannedMessages) do
        out[i] = string.gsub(msg, "/kingdamon", serverBase)
    end
    return out
end

local function pickMessages()
    local msgs = buildMessageList(spamServer)
    local chosen = {}
    for i = 1, 2 do
        if #msgs > 0 then
            local idx = math.random(1, #msgs)
            table.insert(chosen, msgs[idx])
            table.remove(msgs, idx)
        end
    end
    return chosen
end

-- Send chat message with fallbacks
local function sendChatMessage(text)
    local success = false
    print("Attempting chat send:", text)
    if TextChatService and TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
        print("Trying TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync")
        success = pcall(function()
            TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync(text)
        end)
    else
        print("New chat API not available")
    end

    if not success then
        print("Trying legacy system message...")
        pcall(function()
            StarterGui:SetCore("ChatMakeSystemMessage", { Text = text, Color = Color3.new(1, 1, 1) })
            success = true
        end)
    end

    if not success then
        print("Trying old SayMessageRequest...")
        pcall(function()
            local chatEvents = ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents")
            if chatEvents and chatEvents:FindFirstChild("SayMessageRequest") then
                chatEvents.SayMessageRequest:FireServer(text, "All")
                success = true
            end
        end)
    end

    print("sendMessage finished! Success:", success)
    return success
end

-- Follow a player's HumanoidRootPart
local function startFollowing(targetPlayer)
    if followConnection then
        followConnection:Disconnect()
        followConnection = nil
    end
    if not targetPlayer or not targetPlayer.Character or not targetPlayer.Character:FindFirstChild("HumanoidRootPart") then
        return false
    end
    local myChar = localPlayer.Character
    if not myChar or not myChar:FindFirstChild("HumanoidRootPart") then
        return false
    end
    local counter = 0
    followConnection = RunService.Heartbeat:Connect(function()
        counter = counter + 1
        if counter % 3 == 0 then
            pcall(function()
                if targetPlayer and targetPlayer.Character and targetPlayer.Character:FindFirstChild("HumanoidRootPart") then
                    local targetPos = targetPlayer.Character.HumanoidRootPart.Position
                    myChar.HumanoidRootPart.CFrame = CFrame.new(targetPos + Vector3.new(0, 10, 0))
                end
            end)
        end
    end)
    return true
end

local function stopFollowing()
    if followConnection then
        followConnection:Disconnect()
        followConnection = nil
    end
end

local function pickRandomPlayer()
    local candidates = {}
    for _, plr in pairs(Players:GetPlayers()) do
        if plr ~= localPlayer and plr.Character and plr.Character:FindFirstChild("HumanoidRootPart") then
            table.insert(candidates, plr)
        end
    end
    if #candidates > 0 then
        return candidates[math.random(1, #candidates)]
    end
    return nil
end

local function promoteToPlayer()
    local target = pickRandomPlayer()
    if not target then
        wait(0.8)
        return false
    end

    if not startFollowing(target) then
        wait(0.8)
        return false
    end

    wait(0.3)
    local messagesToSend = pickMessages()
    for _, msg in ipairs(messagesToSend) do
        if not autoHopEnabled then break end
        local ok = sendChatMessage(msg)
        print(ok and "[+]" or "[-]", msg)
        wait(math.random(0.8, 1.2))
    end

    wait(0.5)
    stopFollowing()
    return true
end

local function stopScript()
    autoHopEnabled = false
    stopFollowing()
    saveSettings()
    print("Script stopped")
    uiLib:Notify({ Title = "Spammer Stopped", Content = "Stopped promotions.", Duration = 5 })
end

-- Main loop
local function mainLoop()
    math.randomseed(tick())

    UserInputService.InputBegan:Connect(function(input)
        if input.KeyCode == Enum.KeyCode.Q then
            stopScript()
        end
    end)

    local processed = 0
    local limit = maxPerServer

    applyFastFlags()
    applySettingsTweaks()
    hideGuiLoop()
    ensureChatEnabledLoop()
    performanceLoop()

    while autoHopEnabled do
        processed = 0
        while autoHopEnabled and processed < limit do
            if promoteToPlayer() then
                processed = processed + 1
                print("Processed", processed, "/", limit)
                wait(math.random(1, 2))
            else
                wait(1)
            end
        end

        if autoHopEnabled then
            print("Max users reached, teleporting to new server ...")
            saveSettings()
            teleportToAnotherServer()
            wait(20)
        end
    end

    stopScript()
end

-- UI elements
local inputField = tabHome:CreateInput({
    Name = "server you want to mass dm",
    CurrentValue = spamServer,
    PlaceholderText = "Input server example /kingdamon",
    RemoveTextAfterFocusLost = false,
    Flag = "Input1",
    Callback = function(val)
        spamServer = val
        saveSettings()
        print("Mass DM server set to:", spamServer)
        uiLib:Notify({ Title = "Server Set", Content = "Current server: " .. spamServer, Duration = 3 })
    end,
})

local startToggle = tabHome:CreateToggle({
    Name = "Start chat promotion (auto-hop)",
    CurrentValue = autoHopEnabled,
    Flag = "Toggle1",
    Callback = function(val)
        autoHopEnabled = val
        saveSettings()
        if val then
            if spamServer == "" then
                uiLib:Notify({ Title = "Error", Content = "Please enter the server before you start!", Duration = 6 })
                return
            end
            uiLib:Notify({ Title = "Promotion Started", Content = "Script started with server: " .. spamServer, Duration = 4 })
            spawn(mainLoop)
        else
            stopScript()
        end
    end,
})

uiLib:Notify({
    Title = "Script Loaded!",
    Content = "Ready for chat promotions. Input server, then toggle ON. Q = stop.",
    Duration = 7
})

-- Auto-start if configured
task.defer(function()
    if autoHopEnabled and spamServer ~= "" then
        uiLib:Notify({ Title = "Auto Start", Content = "Auto-starting chat promotion after hop.", Duration = 5 })
        spawn(mainLoop)
    end
end)
