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
        settings().Physics.PhysicsEnvironmentalThrottle = Enum.EnviromentalPhysicsThrottle.DefaultAuto
    end)
end

local function disableUI()
    pcall(function()
        StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList, false)
        StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack, false)
        StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Health, false)
        StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.EmotesMenu, false)
        StarterGui:SetCore("TopbarEnabled", false)
    end)
    
    pcall(function()
        local playerGui = player:WaitForChild("PlayerGui", 2)
        if playerGui then
            for _, gui in pairs(playerGui:GetChildren()) do
                if gui:IsA("ScreenGui") and gui.Name ~= "Chat" then
                    gui.Enabled = false
                end
            end
        end
    end)
    
    spawn(function()
        while wait(2) do
            pcall(function()
                if workspace.CurrentCamera then
                    workspace.CurrentCamera.FieldOfView = 30
                end
            end)
        end
    end)
end

local function enableChatFeatures()
    pcall(function()
        StarterGui:SetCoreGuiEnabled(Enum.CoreGuiType.Chat, true)
    end)
    
    pcall(function()
        local playerGui = player:WaitForChild("PlayerGui", 2)
        if playerGui then
            local chatGui = playerGui:FindFirstChild("Chat")
            if chatGui then
                chatGui.Enabled = true
            end
        end
    end)
    
    local attempts = 0
    repeat
        wait(0.2)
        attempts = attempts + 1
        pcall(function()
            if TextChatService.ChatInputBarConfiguration then
                TextChatService.ChatInputBarConfiguration.Enabled = true
            end
        end)
    until attempts > 15 or (TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel)
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

local function missing(t, f, fallback)
    if type(f) == t then return f end
    return fallback
end

local queueteleport = missing("function", queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport))

local gameIds = {
    "105521726700482",
    "6884319169",
    "78699621133325",
    "87206555365816",
    "13278749064",
	"6003577316"
}

local messages = {
    "ageplayer heaven in /brat",
    "cnc and ageplay in vcs /brat",
    "get active /brat",
    "cnc and ageplay in vcs /brat",
    "join the new /brat",
    "camgir1s in /brat jvc",
    "egirls in /brat join"
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
        writefile("spammer_data.json", HttpService:JSONEncode(data))
    end)
end

local function loadScriptData()
    local success, content = pcall(function()
        if isfile and isfile("spammer_data.json") then
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
    while connectionAttempts < 30 do
        local ping = game:GetService("Stats").Network.ServerStatsItem["Data Ping"]:GetValueString()
        local pingValue = tonumber(ping:match("(%d+)"))
        
        if pingValue and pingValue < 300 then
            break
        end
        
        wait(0.5)
        connectionAttempts = connectionAttempts + 1
    end
end

local function waitForGameLoad()
    local attempts = 0
    while (not player.Character or not player.Character:FindFirstChild("Humanoid")) and attempts < 40 do
        wait(0.1)
        attempts = attempts + 1
    end
    
    if not player.Character then
        print("Failed to load character - restarting")
        wait(1)
        teleportToRandomGame()
        return
    end
    
    applyNetworkOptimizations()
    optimizeClientPerformance()
    waitForStableConnection()
    disableUI()
    wait(0.3)
    enableChatFeatures()
    optimizeRendering()
    
    wait(0.5)
    
    attempts = 0
    while attempts < 15 do
        local success = pcall(function()
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                return true
            end
        end)
        
        if success and TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
            break
        end
        
        wait(0.2)
        attempts = attempts + 1
    end
    
    wait(0.3)
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
    
    while not success and attempts < 3 do
        success = pcall(function()
            if TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel then
                TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync(message)
                return true
            end
        end)
        
        if not success then
            attempts = attempts + 1
            wait(0.5)
        end
    end
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
    
    if followPlayer(targetPlayer) then
        wait(0.3)
        
        local selectedMessages = getRandomMessages()
        for i, message in ipairs(selectedMessages) do
            if not isRunning then break end
            sendMessage(message)
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
    
    while httpAttempts < 2 do
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
        if httpAttempts < 2 then
            wait(1)
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
        return lowPingServers[math.random(1, math.min(2, #lowPingServers))]
    elseif #goodServers > 0 then
        return goodServers[math.random(1, math.min(3, #goodServers))]
    else
        return availableServers[1]
    end
end

local function tryTeleportWithRetry(gameId, serverId)
    local maxRetries = 2
    
    for attempt = 1, maxRetries do
        local success, errorMsg = pcall(function()
            if serverId then
                TeleportService:TeleportToPlaceInstance(tonumber(gameId), serverId, player)
            else
                TeleportService:Teleport(tonumber(gameId), player)
            end
        end)
        
        if success then
            return true
        else
            if attempt < maxRetries then
                wait(0.8)
            else
                failedGames[gameId] = tick()
                return false
            end
        end
    end
    
    return false
end

local function getWorkingGameIds()
    local workingIds = {}
    local currentTime = tick()
    
    for _, gameId in ipairs(gameIds) do
        if not failedGames[gameId] or (currentTime - failedGames[gameId] >= 120) then
            table.insert(workingIds, gameId)
        end
    end
    
    return #workingIds > 0 and workingIds or gameIds
end

local function getRandomGameId()
    local workingIds = getWorkingGameIds()
    return workingIds[math.random(1, #workingIds)]
end

local function teleportToRandomGame()
    cleanupOldServers()
    saveScriptData()
    queueScript()
    
    local gameId = getRandomGameId()
    local attempts = 0
    local maxAttempts = 6
    
    while attempts < maxAttempts and isRunning do
        local availableServers = getAvailableServers(gameId)
        
        if #availableServers > 0 then
            local selectedServer = selectBestServer(availableServers)
            
            if selectedServer then
                joinedServers[selectedServer.id] = tick()
                saveScriptData()
                
                if tryTeleportWithRetry(gameId, selectedServer.id) then
                    return
                end
            end
        end
        
        if attempts > 2 then
            if tryTeleportWithRetry(gameId, nil) then
                return
            end
            wait(0.3)
        end
        
        attempts = attempts + 1
        wait(0.8)
    end
    
    wait(math.random(1, 2))
    if isRunning then
        teleportToRandomGame()
    end
end

local function startSpamming()
    spawn(function()
        waitForGameLoad()
        
        if not isRunning then return end
        
        local processedInThisGame = 0
        
        while processedInThisGame < maxUsersPerGame and isRunning do
            if processUser() then
                processedInThisGame = processedInThisGame + 1
                usersProcessed = usersProcessed + 1
                saveScriptData()
                wait(math.random(0.8, 1.5))
            else
                wait(1)
            end
        end
        
        if isRunning then
            usersProcessed = 0
            saveScriptData()
            wait(0.5)
            teleportToRandomGame()
        end
    end)
end

local function stopSpamming()
    isRunning = false
    stopFollowing()
    saveScriptData()
end

local function onKeyPress(key)
    if key.KeyCode == Enum.KeyCode.Q then
        stopSpamming()
    elseif key.KeyCode == Enum.KeyCode.R then
        teleportToRandomGame()
    end
end

local function initialize()
    loadScriptData()
    
    UserInputService.InputBegan:Connect(onKeyPress)
    
    if game.JobId and game.JobId ~= "" then
        joinedServers[game.JobId] = tick()
    end
    
    startSpamming()
end

initialize()
