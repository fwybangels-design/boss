-- Rayfield chat promotion script with:
-- - serverhop after max DM'd users
-- - auto-execute after hop
-- - auto-save/restore of input/toggle settings
-- - autostart promotion if toggle was ON in previous run
-- Place in your executor's script folder, or host on GitHub for auto-execute. No manual file creation needed.

local Rayfield = loadstring(game:HttpGet('https://sirius.menu/rayfield'))()
local Window = Rayfield:CreateWindow({
    Name = "chat promotion script",
    Theme = "Default",
    ToggleUIKeybind = "K"
})
local MainTab = Window:CreateTab("Home")
local MainSection = MainTab:CreateSection("Main")

local Players = game:GetService("Players")
local TextChatService = game:GetService("TextChatService")
local UserInputService = game:GetService("UserInputService")
local StarterGui = game:GetService("StarterGui")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TeleportService = game:GetService("TeleportService")
local HttpService = game:GetService("HttpService")
local player = Players.LocalPlayer

local SETTINGS_FILE = "chatpromotion_settings.json"

local spamServer = ""
local isRunning = false
local maxUsersPerGame = 5
local followConnection = nil

local rawMessages = {
    "ageplayer heaven in /kingdamon",
    "cnc and ageplay in vcs /kingdamon",
    "get active /kingdamon",
    "cnc and ageplay in vcs /kingdamon",
    "join the new /kingdamon",
    "camgir1s in /kingdamon jvc",
    "yo jvc rn she going crazy /kingdamon",
    "YO WHAT ARE THEY DOING ON CAM /kingdamon",
    "BRO WHAT IS SHE DOING ON CAM /kingdamon",
    "STAG3 GIRLS IN /kingdamon"
}

-- ==== Auto-save/load settings routines ====
local function saveSettings()
    local toSave = {
        spamServer = spamServer,
        autoHopEnabled = isRunning
    }
    if writefile then
        writefile(SETTINGS_FILE, HttpService:JSONEncode(toSave))
    end
end

local function loadSettings()
    if isfile and isfile(SETTINGS_FILE) then
        local data = HttpService:JSONDecode(readfile(SETTINGS_FILE))
        spamServer = data.spamServer or "/kingdamon"
        isRunning = data.autoHopEnabled or false
    end
end

loadSettings()

-- ==== Optimization routines ====
local function applyNetworkOptimizations()
    local flags = {
        DFIntTaskSchedulerTargetFps = 20, FFlagDebugDisableInGameMenuV2 = true, FFlagDisableInGameMenuV2 = true,
        DFIntTextureQualityOverride = 1, FFlagRenderNoLights = true, FFlagRenderNoShadows = true,
        DFIntDebugFRMQualityLevelOverride = 1, DFFlagTextureQualityOverrideEnabled = true,
        FFlagHandleAltEnterFullscreenManually = false, DFIntConnectionMTUSize = 1200,
        DFIntMaxMissedWorldStepsRemembered = 1, DFIntDefaultTimeoutTimeMs = 3000,
        FFlagDebugSimIntegrationStabilityTesting = false, DFFlagDebugRenderForceTechnologyVoxel = true,
        FFlagUserHandleCameraToggle = false
    }
    for flag, value in pairs(flags) do pcall(function() game:SetFastFlag(flag, value) end) end
end
local function optimizeClientPerformance()
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
local function forceDisableUI()
    spawn(function()
        while isRunning do
            pcall(function()
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.EmotesMenu, false)
                StarterGui:SetCore("TopbarEnabled", false)
            end)
            pcall(function()
                local playerGui = player:FindFirstChild("PlayerGui")
                if playerGui then
                    for _, gui in pairs(playerGui:GetChildren()) do
                        if gui:IsA("ScreenGui") and gui.Name ~= "Chat" then gui.Enabled = false end
                    end
                end
            end)
            pcall(function()
                if workspace.CurrentCamera then workspace.CurrentCamera.FieldOfView = 30 end
            end)
            wait(1)
        end
    end)
end
local function forceChatFeatures()
    spawn(function()
        while isRunning do
            pcall(function() StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, true) end)
            pcall(function()
                local playerGui = player:FindFirstChild("PlayerGui")
                if playerGui then
                    local chatGui = playerGui:FindFirstChild("Chat")
                    if chatGui then chatGui.Enabled = true end
                end
            end)
            pcall(function()
                if TextChatService.ChatInputBarConfiguration then TextChatService.ChatInputBarConfiguration.Enabled = true end
            end)
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                break
            end
            wait(0.5)
        end
    end)
end
local function optimizeRendering()
    spawn(function()
        local heartbeatCount = 0
        RunService.Heartbeat:Connect(function()
            heartbeatCount += 1
            if heartbeatCount % 30 == 0 then
                pcall(function()
                    for _, obj in pairs(workspace:GetDescendants()) do
                        if obj:IsA("Decal") or obj:IsA("Texture") then obj.Transparency = 1 end
                        if obj:IsA("ParticleEmitter") or obj:IsA("Smoke") or obj:IsA("Sparkles") or obj:IsA("Fire") then obj.Enabled = false end
                        if obj:IsA("Sound") then obj.Volume = 0 end
                    end
                end)
            end
        end)
    end)
end

local function getAvailableServers(placeId)
    local availableServers = {}
    local success, result = pcall(function()
        return game:HttpGet("https://games.roblox.com/v1/games/" .. placeId .. "/servers/Public?sortOrder=Asc&limit=100", true)
    end)
    if success then
        local data = HttpService:JSONDecode(result)
        for _, server in ipairs(data and data.data or {}) do
            if server and server.id and server.playing and server.maxPlayers and
               server.playing < server.maxPlayers and server.id ~= game.JobId then
                table.insert(availableServers, server.id)
            end
        end
    end
    return availableServers
end

local function teleportToNewServer()
    local available = getAvailableServers(game.PlaceId)
    local chosen = available[math.random(1, math.max(1, #available))]
    if chosen then
        print("Teleporting to new server:", chosen)
        local queueteleport = queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport)
        if queueteleport and type(queueteleport) == "function" then
            queueteleport([[
wait(1)
loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()
]])
        end
        TeleportService:TeleportToPlaceInstance(game.PlaceId, chosen, Players.LocalPlayer)
    else
        print("No available servers found; retrying soon.")
        wait(8)
        teleportToNewServer()
    end
end

local function buildMessages(serverName)
    local repl = serverName ~= "" and serverName or "/kingdamon"
    local res = {}
    for i, msg in ipairs(rawMessages) do
        res[i] = string.gsub(msg, "/kingdamon", repl)
    end
    return res
end

local function getRandomMessages()
    local pool = buildMessages(spamServer)
    local result = {}
    for i = 1, 2 do
        if #pool > 0 then
            local idx = math.random(1, #pool)
            table.insert(result, pool[idx])
            table.remove(pool, idx)
        end
    end
    return result
end

local function sendMessage(message)
    local success = false
    local attempts = 0
    print("Attempting chat send:", message)
    if TextChatService and TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
        print("Trying TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync")
        success = pcall(function()
            TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync(message)
        end)
    else
        print("New chat API not available")
    end
    if not success then
        print("Trying legacy system message...")
        pcall(function()
            StarterGui:SetCore("ChatMakeSystemMessage", {Text = message, Color = Color3.new(1,1,1)})
            success = true
        end)
    end
    if not success then
        print("Trying old SayMessageRequest...")
        pcall(function()
            local chatEvent = ReplicatedStorage:FindFirstChild("DefaultChatSystemChatEvents")
            if chatEvent and chatEvent:FindFirstChild("SayMessageRequest") then
                chatEvent.SayMessageRequest:FireServer(message, "All")
                success = true
            end
        end)
    end
    print("sendMessage finished! Success:", success)
    return success
end

local function followPlayer(targetPlayer)
    if followConnection then
        followConnection:Disconnect()
        followConnection = nil
    end
    if not targetPlayer or not targetPlayer.Character or not targetPlayer.Character:FindFirstChild("HumanoidRootPart") then return false end
    local chr = player.Character
    if not chr or not chr:FindFirstChild("HumanoidRootPart") then return false end
    local updateCount = 0
    followConnection = RunService.Heartbeat:Connect(function()
        updateCount += 1
        if updateCount % 3 == 0 then
            pcall(function()
                if targetPlayer and targetPlayer.Character and targetPlayer.Character:FindFirstChild("HumanoidRootPart") then
                    local pos = targetPlayer.Character.HumanoidRootPart.Position
                    chr.HumanoidRootPart.CFrame = CFrame.new(pos + Vector3.new(0,10,0))
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

local function getRandomPlayer()
    local candidates = {}
    for _, p in pairs(Players:GetPlayers()) do
        if p ~= player and p.Character and p.Character:FindFirstChild("HumanoidRootPart") then
            table.insert(candidates, p)
        end
    end
    if #candidates > 0 then
        return candidates[math.random(1, #candidates)]
    end
    return nil
end

local function processUser()
    local targetPlayer = getRandomPlayer()
    if not targetPlayer then wait(0.8) return false end
    followPlayer(targetPlayer)
    wait(0.3)
    local msgs = getRandomMessages()
    for _, message in ipairs(msgs) do
        if not isRunning then break end
        local sent = sendMessage(message)
        print(sent and "[+]" or "[-]", message)
        wait(math.random(0.8, 1.2))
    end
    wait(0.5)
    stopFollowing()
    return true
end

local function stopSpamming()
    isRunning = false
    stopFollowing()
    saveSettings()
    print("Script stopped")
    Rayfield:Notify({
        Title = "Spammer Stopped",
        Content = "Stopped promotions.",
        Duration = 5,
    })
end

local function spamLoop()
    math.randomseed(tick())
    UserInputService.InputBegan:Connect(function(key)
        if key.KeyCode == Enum.KeyCode.Q then
            stopSpamming()
        end
    end)
    local processed = 0
    local maxPerRun = maxUsersPerGame

    applyNetworkOptimizations()
    optimizeClientPerformance()
    forceDisableUI()
    forceChatFeatures()
    optimizeRendering()

    while isRunning do
        processed = 0
        while isRunning and processed < maxPerRun do
            if processUser() then
                processed = processed + 1
                print("Processed", processed, "/", maxPerRun)
                wait(math.random(1,2))
            else
                wait(1)
            end
        end
        if isRunning then
            print("Max users reached, teleporting to new server ...")
            saveSettings()
            teleportToNewServer()
            wait(20)
        end
    end
    stopSpamming()
end

local Input = MainTab:CreateInput({
    Name = "server you want to mass dm",
    CurrentValue = spamServer,
    PlaceholderText = "Input server example /kingdamon",
    RemoveTextAfterFocusLost = false,
    Flag = "Input1",
    Callback = function(Text)
        spamServer = Text
        saveSettings()
        print("Mass DM server set to:", spamServer)
        Rayfield:Notify({
            Title = "Server Set",
            Content = "Current server: "..spamServer,
            Duration = 3,
        })
    end,
})

local Toggle = MainTab:CreateToggle({
    Name = "Start chat promotion (auto-hop)",
    CurrentValue = isRunning,
    Flag = "Toggle1",
    Callback = function(Value)
        isRunning = Value
        saveSettings()
        if Value then
            if spamServer == "" then
                Rayfield:Notify({
                    Title = "Error",
                    Content = "Please enter the server before you start!",
                    Duration = 6,
                })
                return
            end
            Rayfield:Notify({
                Title = "Promotion Started",
                Content = "Script started with server: "..spamServer,
                Duration = 4,
            })
            spawn(spamLoop)
        else
            stopSpamming()
        end
    end,
})

Rayfield:Notify({Title="Script Loaded!",Content="Ready for chat promotions. Input server, then toggle ON. Q = stop.",Duration=7})

-- AUTO-START PROMOTION after serverhop/auto-execute if toggle was ON
if isRunning and spamServer ~= "" then
    spawn(spamLoop)
end
