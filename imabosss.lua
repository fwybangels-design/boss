local Players = game:GetService("Players")
local TeleportService = game:GetService("TeleportService")
local TextChatService = game:GetService("TextChatService")
local UserInputService = game:GetService("UserInputService")
local HttpService = game:GetService("HttpService")
local StarterGui = game:GetService("StarterGui")
local CoreGui = game:GetService("CoreGui")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local player = Players.LocalPlayer
local isRunning = true
local joinedServers = {}
local failedGames = {}
local currentTargetPlayer = nil
local usersProcessed = 0
local maxUsersPerGame = 5
local followConnection = nil
local pingOptimized = false

local function applyNetworkOptimizations()
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
    
    for flag, value in pairs(flags) do
        pcall(function()
            game:SetFastFlag(flag, value)
        end)
    end
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
        while wait(1) do
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
                        if gui:IsA("ScreenGui") and gui.Name ~= "Chat" then
                            gui.Enabled = false
                        end
                    end
                end
            end)
            
            pcall(function()
                if workspace.CurrentCamera then
                    workspace.CurrentCamera.FieldOfView = 30
                end
            end)
        end
    end)
end

local function forceChatFeatures()
    spawn(function()
        while wait(0.5) do
            pcall(function()
                StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, true)
            end)
            
            pcall(function()
                local playerGui = player:FindFirstChild("PlayerGui")
                if playerGui then
                    local chatGui = playerGui:FindFirstChild("Chat")
                    if chatGui then
                        chatGui.Enabled = true
                    end
                end
            end)
            
            pcall(function()
                if TextChatService.ChatInputBarConfiguration then
                    TextChatService.ChatInputBarConfiguration.Enabled = true
                end
            end)
            
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                break
            end
        end
    end)
end

local function optimizeRendering()
    spawn(function()
        local heartbeatCount = 0
        RunService.Heartbeat:Connect(function()
            heartbeatCount = heartbeatCount + 1
            if heartbeatCount % 30 == 0 then
                pcall(function()
                    for _, obj in pairs(workspace:GetDescendants()) do
                        if obj:IsA("Decal") or obj:IsA("Texture") then
                            obj.Transparency = 1
                        elseif obj:IsA("ParticleEmitter") or obj:IsA("Smoke") or obj:IsA("Sparkles") or obj:IsA("Fire") then
                            obj.Enabled = false
                        elseif obj:IsA("Sound") then
                            obj.Volume = 0
                        end
                    end
                end)
            end
        end)
    end)
end

local queueteleport = queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport)

local messages = {
    "ageplayer heaven in /brat",
    "cnc and ageplay in vcs /brat",
    "get active /brat",
    "cnc and ageplay in vcs /brat",
    "join the new /brat",
    "camgir1s in /brat jvc",
	"yo jvc rn she going crazy /brat",
	"YO WHAT ARE THEY DOING ON CAM /brat",
	"BRO WHAT IS SHE DOING ON CAM /brat",
	"STAG3 GIRLS IN /brat"
}

local function queueScript()
    if queueteleport and type(queueteleport) == "function" then
        queueteleport([[
wait(0.5)
print("Restarting script from queue...")
pcall(function()
    loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()
end)
]])
    else
        print("Queue teleport not available - script will not auto-restart")
    end
end

local function saveScriptData()
    local data = {
        joinedServers = joinedServers,
        shouldAutoStart = isRunning,
        failedGames = failedGames,
        usersProcessed = usersProcessed
    }
    pcall(function()
        if writefile then
            writefile("spammer_data.json", HttpService:JSONEncode(data))
        end
    end)
end

local function loadScriptData()
    local success, content = pcall(function()
        if isfile and readfile and isfile("spammer_data.json") then
            return readfile("spammer_data.json")
        end
        return nil
    end)
    
    if success and content then
        local success2, data = pcall(function()
            return HttpService:JSONDecode(content)
        end)
        
        if success2 and data then
            joinedServers = data.joinedServers or {}
            failedGames = data.failedGames or {}
            usersProcessed = data.usersProcessed or 0
            return data.shouldAutoStart or false
        end
    end
    return false
end

local function waitForStableConnection()
    local connectionAttempts = 0
    while connectionAttempts < 20 do
        pcall(function()
            local ping = game:GetService("Stats").Network.ServerStatsItem["Data Ping"]:GetValueString()
            local pingValue = tonumber(ping:match("(%d+)"))
            
            if pingValue and pingValue < 300 then
                return true
            end
        end)
        
        wait(0.3)
        connectionAttempts = connectionAttempts + 1
    end
end

local function waitForGameLoad()
    print("Starting game load sequence...")
    
    local attempts = 0
    while (not player.Character or not player.Character:FindFirstChild("Humanoid")) and attempts < 50 do
        wait(0.1)
        attempts = attempts + 1
    end
    
    if not player.Character then
        print("Failed to load character - restarting")
        wait(2)
        teleportToNewServer()
        return
    end
    
    print("Character loaded, applying optimizations...")
    applyNetworkOptimizations()
    optimizeClientPerformance()
    waitForStableConnection()
    
    print("Disabling UI and enabling chat...")
    forceDisableUI()
    forceChatFeatures()
    optimizeRendering()
    
    wait(2)
    
    local chatAttempts = 0
    while chatAttempts < 30 do
        local chatReady = false
        pcall(function()
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                chatReady = true
            end
        end)
        
        if chatReady then
            print("Chat system ready!")
            break
        end
        
        wait(0.3)
        chatAttempts = chatAttempts + 1
    end
    
    print("Game load sequence complete!")
    wait(1)
end

local function cleanupOldServers()
    local currentTime = tick()
    for serverId, joinTime in pairs(joinedServers) do
        if currentTime - joinTime >= 60 then
            joinedServers[serverId] = nil
        end
    end
    
    for gameId, failTime in pairs(failedGames) do
        if currentTime - failTime >= 120 then
            failedGames[gameId] = nil
        end
    end
end

local function sendMessage(message)
    local success = false
    local attempts = 0
    
    while not success and attempts < 5 do
        success = pcall(function()
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync(message)
                return true
            end
        end)
        
        if not success then
            attempts = attempts + 1
            wait(0.3)
        end
    end
    
    return success
end

local function getRandomMessages()
    local selectedMessages = {}
    local availableMessages = {}
    
    for i, msg in ipairs(messages) do
        table.insert(availableMessages, msg)
    end
    
    for i = 1, 2 do
        if #availableMessages > 0 then
            local randomIndex = math.random(1, #availableMessages)
            table.insert(selectedMessages, availableMessages[randomIndex])
            table.remove(availableMessages, randomIndex)
        end
    end
    
    return selectedMessages
end

local function stopFollowing()
    if followConnection then
        followConnection:Disconnect()
        followConnection = nil
    end
end

local function followPlayer(targetPlayer)
    stopFollowing()
    
    if not targetPlayer or not targetPlayer.Character or not targetPlayer.Character:FindFirstChild("HumanoidRootPart") then
        return false
    end
    
    local character = player.Character
    if not character or not character:FindFirstChild("HumanoidRootPart") then
        return false
    end
    
    local updateCount = 0
    followConnection = RunService.Heartbeat:Connect(function()
        updateCount = updateCount + 1
        if updateCount % 3 == 0 then
            pcall(function()
                if targetPlayer and targetPlayer.Character and targetPlayer.Character:FindFirstChild("HumanoidRootPart") then
                    local targetPosition = targetPlayer.Character.HumanoidRootPart.Position
                    local newPosition = targetPosition + Vector3.new(0, 10, 0)
                    character.HumanoidRootPart.CFrame = CFrame.new(newPosition)
                end
            end)
        end
    end)
    
    return true
end

local function getRandomPlayer()
    local players = {}
    for _, p in pairs(Players:GetPlayers()) do
        if p ~= player and p.Character and p.Character:FindFirstChild("HumanoidRootPart") then
            table.insert(players, p)
        end
    end
    
    if #players > 0 then
        return players[math.random(1, #players)]
    end
    return nil
end

local function processUser()
    local targetPlayer = getRandomPlayer()
    if not targetPlayer then
        wait(0.8)
        return false
    end
    
    print("Processing user: " .. targetPlayer.Name)
    
    if followPlayer(targetPlayer) then
        wait(0.3)
        
        local selectedMessages = getRandomMessages()
        for i, message in ipairs(selectedMessages) do
            if not isRunning then break end
            local sent = sendMessage(message)
            if sent then
                print("Sent message: " .. message)
            else
                print("Failed to send message")
            end
            wait(math.random(0.8, 1.2))
        end
        
        wait(0.5)
        stopFollowing()
        return true
    end
    
    return false
end

local function getAvailableServers(gameId)
    local availableServers = {}
    local httpAttempts = 0
    
    while httpAttempts < 3 do
        local success, result = pcall(function()
            return game:HttpGet("https://games.roblox.com/v1/games/" .. gameId .. "/servers/Public?sortOrder=Asc&limit=100", true)
        end)
        
        if success then
            local parseSuccess, data = pcall(function()
                return HttpService:JSONDecode(result)
            end)
            
            if parseSuccess and data and data.data and type(data.data) == "table" then
                for _, server in ipairs(data.data) do
                    if server and 
                       server.id and 
                       server.playing and 
                       server.maxPlayers and
                       server.ping and
                       server.playing >= 2 and
                       server.playing < server.maxPlayers * 0.8 and
                       server.ping < 200 and
                       server.id ~= game.JobId and 
                       not joinedServers[server.id] then
                        table.insert(availableServers, {
                            id = server.id,
                            playing = server.playing,
                            maxPlayers = server.maxPlayers,
                            ping = server.ping,
                            priority = server.playing - (server.ping / 10)
                        })
                    end
                end
                
                table.sort(availableServers, function(a, b)
                    return a.priority > b.priority
                end)
                break
            end
        end
        
        httpAttempts = httpAttempts + 1
        if httpAttempts < 3 then
            wait(2)
        end
    end
    
    return availableServers
end

local function selectBestServer(availableServers)
    if #availableServers == 0 then
        return nil
    end
    
    local lowPingServers = {}
    local goodServers = {}
    
    for _, server in ipairs(availableServers) do
        local populationRatio = server.playing / server.maxPlayers
        if server.ping < 100 and server.playing >= 3 and populationRatio >= 0.15 and populationRatio <= 0.75 then
            table.insert(lowPingServers, server)
        elseif server.ping < 150 and server.playing >= 2 and populationRatio <= 0.8 then
            table.insert(goodServers, server)
        end
    end
    
    if #lowPingServers > 0 then
        return lowPingServers[math.random(1, math.min(3, #lowPingServers))]
    elseif #goodServers > 0 then
        return goodServers[math.random(1, math.min(5, #goodServers))]
    else
        return availableServers[math.random(1, math.min(3, #availableServers))]
    end
end

local function tryTeleportWithRetry(gameId, serverId)
    local maxRetries = 3
    
    for attempt = 1, maxRetries do
        local success, errorMsg = pcall(function()
            wait(0.5)
            
            if serverId then
                TeleportService:TeleportToPlaceInstance(tonumber(gameId), serverId, player)
            else
                TeleportService:Teleport(tonumber(gameId), player)
            end
        end)
        
        if success then
            return true
        else
            print("Teleport attempt " .. attempt .. " failed: " .. tostring(errorMsg))
            
            if string.find(tostring(errorMsg), "773") or string.find(tostring(errorMsg), "restricted") then
                print("Place is restricted or session conflict - trying different approach")
                wait(2)
                
                local logoutSuccess = pcall(function()
                    game:GetService("GuiService"):Logout()
                end)
                
                if logoutSuccess then
                    wait(3)
                end
            end
            
            if attempt < maxRetries then
                wait(math.random(2, 4))
            else
                failedGames[gameId] = tick()
                return false
            end
        end
    end
    
    return false
end

local function teleportToNewServer()
    cleanupOldServers()
    saveScriptData()
    queueScript()
    
    wait(math.random(1, 2))
    
    local currentGameId = tostring(game.PlaceId)
    local attempts = 0
    local maxAttempts = 8
    
    while attempts < maxAttempts and isRunning do
        print("Server search attempt " .. (attempts + 1) .. " for current game: " .. currentGameId)
        
        local availableServers = getAvailableServers(currentGameId)
        
        if #availableServers > 0 then
            local selectedServer = selectBestServer(availableServers)
            
            if selectedServer then
                joinedServers[selectedServer.id] = tick()
                saveScriptData()
                
                print("Attempting to join new server: " .. selectedServer.id)
                if tryTeleportWithRetry(currentGameId, selectedServer.id) then
                    return
                end
            end
        end
        
        print("No suitable servers found, trying random server hop...")
        if tryTeleportWithRetry(currentGameId, nil) then
            return
        end
        
        attempts = attempts + 1
        wait(math.random(4, 8))
    end
    
    print("All server hop attempts failed, retrying in 15 seconds...")
    wait(15)
    if isRunning then
        teleportToNewServer()
    end
end

local function startSpamming()
    spawn(function()
        waitForGameLoad()
        
        if not isRunning then return end
        
        print("Starting spam process...")
        local processedInThisGame = 0
        
        while processedInThisGame < maxUsersPerGame and isRunning do
            if processUser() then
                processedInThisGame = processedInThisGame + 1
                usersProcessed = usersProcessed + 1
                saveScriptData()
                print("Processed " .. processedInThisGame .. "/" .. maxUsersPerGame .. " users")
                wait(math.random(1, 2))
            else
                wait(1)
            end
        end
        
        if isRunning then
            print("Max users reached, hopping to new server...")
            usersProcessed = 0
            saveScriptData()
            wait(1)
            teleportToNewServer()
        end
    end)
end

local function stopSpamming()
    isRunning = false
    stopFollowing()
    saveScriptData()
    print("Script stopped")
end

local function onKeyPress(key)
    if key.KeyCode == Enum.KeyCode.Q then
        stopSpamming()
    elseif key.KeyCode == Enum.KeyCode.R then
        teleportToNewServer()
    end
end

local function initialize()
    print("Initializing spammer script...")
    loadScriptData()
    
    UserInputService.InputBegan:Connect(onKeyPress)
    
    if game.JobId and game.JobId ~= "" then
        joinedServers[game.JobId] = tick()
    end
    
    startSpamming()
end

initialize()


