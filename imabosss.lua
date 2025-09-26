-- SANITIZED / DEBUG-FRIENDLY VERSION
-- Note: sendMessage is stubbed (prints only) to avoid posting chat.
-- Replace with a compliant sendMessage implementation yourself if/when messages are safe.

local Players = game:GetService("Players")
local TeleportService = game:GetService("TeleportService")
local TextChatService = game:GetService("TextChatService")
local UserInputService = game:GetService("UserInputService")
local HttpService = game:GetService("HttpService")
local StarterGui = game:GetService("StarterGui")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer
local isRunning = true
local joinedServers = {}
local failedGames = {}
local messagesSent = false

local function applyFastFlags()
    local flags = {
        DFIntTaskSchedulerTargetFps = 15,
        FFlagDebugDisableInGameMenuV2 = true,
        FFlagDisableInGameMenuV2 = true,
        DFIntTextureQualityOverride = 1,
        FFlagRenderNoLights = true,
        FFlagRenderNoShadows = true,
        DFIntDebugFRMQualityLevelOverride = 1,
        DFFlagTextureQualityOverrideEnabled = true,
        FFlagHandleAltEnterFullscreenManually = false
    }

    for flag, value in pairs(flags) do
        pcall(function()
            -- most environments won't allow changing fast flags; keep pcall to avoid errors
            if game.SetFastFlag then
                game:SetFastFlag(flag, value)
            end
        end)
    end
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
        local playerGui = player:WaitForChild("PlayerGui", 5)
        if playerGui then
            for _, gui in pairs(playerGui:GetChildren()) do
                if gui:IsA("ScreenGui") and gui.Name ~= "Chat" then
                    gui.Enabled = false
                end
            end
        end
    end)

    spawn(function()
        while wait(1) do
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
        local playerGui = player:WaitForChild("PlayerGui", 5)
        if playerGui then
            local chatGui = playerGui:FindFirstChild("Chat")
            if chatGui then
                chatGui.Enabled = true
            end
        end
    end)

    local attempts = 0
    repeat
        wait(0.5)
        attempts = attempts + 1
        pcall(function()
            if TextChatService.ChatInputBarConfiguration then
                TextChatService.ChatInputBarConfiguration.Enabled = true
            end
        end)
    until attempts > 20 or (TextChatService.ChatInputBarConfiguration and TextChatService.ChatInputBarConfiguration.TargetTextChannel)
end

local function optimizeRendering()
    pcall(function()
        settings().Rendering.QualityLevel = 1
        settings().Rendering.MeshPartDetailLevel = Enum.MeshPartDetailLevel.Level01
        settings().Rendering.MaterialQualityLevel = Enum.MaterialQualityLevel.Level01
    end)

    spawn(function()
        RunService.Heartbeat:Connect(function()
            pcall(function()
                for _, obj in pairs(workspace:GetDescendants()) do
                    if obj:IsA("Decal") or obj:IsA("Texture") then
                        obj.Transparency = 1
                    elseif obj:IsA("ParticleEmitter") or obj:IsA("Smoke") or obj:IsA("Sparkles") or obj:IsA("Fire") then
                        obj.Enabled = false
                    end
                end
            end)
        end)
    end)
end

local function missing(t, f, fallback)
    if type(f) == t then return f end
    return fallback
end

-- queue_on_teleport detection (exploit envs). leave as-is.
local queueteleport = missing("function", queue_on_teleport or (syn and syn.queue_on_teleport) or (fluxus and fluxus.queue_on_teleport))

local gameIds = {
    "6218169544",
    "6884319169",
    "78699621133325",
    "17255098561",
    "87206555365816",
    "13278749064",
    "6003577316"
}

-- NOTE: messages are not sent by this sanitized script. This array is left as placeholder; DO NOT
-- rely on this script to post chat. sendMessage below prints only.
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
wait(2)
print("Restarting script from queue...")
pcall(function()
    loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()
end)
]])
    else
        print("Queue teleport not available - script will not auto-restart")
    end
end

local function rejoinServer()
    queueScript()
    pcall(function()
        -- Attempt to rejoin previous instance. GetPlayerPlaceInstanceAsync might be restricted in some envs.
        local ok, placeInfo = pcall(function()
            return TeleportService:GetPlayerPlaceInstanceAsync(player.UserId)
        end)
        if ok and placeInfo and placeInfo.PlaceId and placeInfo.InstanceId then
            TeleportService:TeleportToPlaceInstance(placeInfo.PlaceId, placeInfo.InstanceId, player)
        else
            TeleportService:Teleport(game.PlaceId, player)
        end
    end)
end

local function saveScriptData()
    local data = {
        joinedServers = joinedServers,
        shouldAutoStart = isRunning,
        failedGames = failedGames
    }
    pcall(function()
        if writefile then
            writefile("spammer_data.json", HttpService:JSONEncode(data))
        end
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
            return data.shouldAutoStart or false
        end
    end
    return false
end

local function waitForGameLoad()
    local attempts = 0
    while (not player.Character or not player.Character:FindFirstChild("Humanoid")) and attempts < 100 do
        wait(0.1)
        attempts = attempts + 1
    end

    if not player.Character then
        warn("Failed to load character - attempting rejoin")
        wait(5)
        rejoinServer()
        return
    end

    applyFastFlags()
    disableUI()
    wait(2)
    enableChatFeatures()
    optimizeRendering()

    wait(3)

    attempts = 0
    while attempts < 50 do
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

    wait(1)
end

local function cleanupOldServers()
    local currentTime = tick()
    for serverId, joinTime in pairs(joinedServers) do
        if currentTime - joinTime >= 600 then
            joinedServers[serverId] = nil
        end
    end

    for gameId, failTime in pairs(failedGames) do
        if currentTime - failTime >= 300 then
            failedGames[gameId] = nil
        end
    end
end

-- SANITIZED sendMessage: prints only. This prevents banned/illegal messages from being posted.
-- If you remove this stub later, make sure the messages are safe & compliant before enabling.
local function sendMessage(message)
    -- Do NOT post to TextChatService here. Just print for debug.
    print("[SANITIZED sendMessage] would send:", tostring(message))
end

local function getRandomMessages()
    local selectedMessages = {}
    local availableMessages = {}

    for i, msg in ipairs(messages) do
        table.insert(availableMessages, msg)
    end

    for i = 1, 3 do
        if #availableMessages > 0 then
            local randomIndex = math.random(1, #availableMessages)
            table.insert(selectedMessages, availableMessages[randomIndex])
            table.remove(availableMessages, randomIndex)
        end
    end

    return selectedMessages
end

local function getAvailableServers(gameId)
    local availableServers = {}
    local numericGameId = tonumber(gameId)
    if not numericGameId then return availableServers end

    local success, result = pcall(function()
        return game:HttpGet("https://games.roblox.com/v1/games/" .. numericGameId .. "/servers/Public?sortOrder=Asc&limit=100", true)
    end)

    if success and result then
        local parseSuccess, data = pcall(function()
            return HttpService:JSONDecode(result)
        end)

        if parseSuccess and data and data.data and type(data.data) == "table" then
            for _, server in ipairs(data.data) do
                if server and server.id and server.playing and server.maxPlayers and
                   server.playing > 0 and server.playing < server.maxPlayers * 0.8 and
                   tostring(server.id) ~= tostring(game.JobId) and not joinedServers[server.id] then

                    table.insert(availableServers, {
                        id = server.id,
                        playing = server.playing,
                        maxPlayers = server.maxPlayers,
                        priority = server.playing
                    })
                end
            end

            table.sort(availableServers, function(a, b)
                return a.priority < b.priority
            end)
        end
    else
        warn("Failed to fetch servers for", numericGameId)
    end

    return availableServers
end

local function selectBestServer(availableServers)
    if #availableServers == 0 then return nil end

    local lowPopulationServers = {}
    local mediumPopulationServers = {}

    for _, server in ipairs(availableServers) do
        local populationRatio = server.playing / math.max(1, server.maxPlayers)
        if populationRatio < 0.3 then
            table.insert(lowPopulationServers, server)
        elseif populationRatio < 0.6 then
            table.insert(mediumPopulationServers, server)
        end
    end

    if #lowPopulationServers > 0 then
        return lowPopulationServers[math.random(1, #lowPopulationServers)]
    elseif #mediumPopulationServers > 0 then
        return mediumPopulationServers[math.random(1, #mediumPopulationServers)]
    else
        return availableServers[math.random(1, math.min(5, #availableServers))]
    end
end

-- Teleport failure detection via TeleportInitFailed event
local lastTeleportFailed = nil
TeleportService.TeleportInitFailed:Connect(function(plr, teleportResult, errorMessage)
    if plr == player then
        lastTeleportFailed = {
            result = teleportResult,
            message = errorMessage,
            time = tick()
        }
        warn("TeleportInitFailed:", teleportResult, errorMessage)
    end
end)

-- Improved retry that waits for TeleportInitFailed to fire (if teleport fails immediately)
local function tryTeleportWithRetry(gameId, serverId)
    local maxRetries = 3
    local baseDelay = 1

    for attempt = 1, maxRetries do
        lastTeleportFailed = nil
        local ok, callErr = pcall(function()
            if serverId then
                TeleportService:TeleportToPlaceInstance(tonumber(gameId), serverId, player)
            else
                TeleportService:Teleport(tonumber(gameId), player)
            end
        end)

        -- If TeleportService call itself errored (very rare), log it and continue
        if not ok then
            warn("Teleport API call error (pcall):", tostring(callErr))
            if attempt < maxRetries then
                wait(baseDelay * attempt)
                continue
            else
                failedGames[gameId] = tick()
                return false
            end
        end

        -- Teleport usually hands control to Roblox client; if it fails, TeleportInitFailed fires.
        -- Wait a short window to see if failure is reported; if nothing reported assume success (client moved)
        local waited = 0
        local waitTimeout = 6 -- seconds to wait for failure event
        while waited < waitTimeout do
            if lastTeleportFailed then
                -- failure detected
                warn(("Teleport failed for place %s (attempt %d): %s"):format(tostring(gameId), attempt, tostring(lastTeleportFailed.message)))
                break
            end
            wait(0.25)
            waited = waited + 0.25
        end

        if lastTeleportFailed then
            if attempt < maxRetries then
                wait(baseDelay * attempt)
            else
                failedGames[gameId] = tick()
                return false
            end
        else
            -- no failure reported within window — assume teleport succeeded (client transferred)
            return true
        end
    end

    return false
end

local function getWorkingGameIds()
    local workingIds = {}
    local currentTime = tick()

    for _, gameId in ipairs(gameIds) do
        local gid = tostring(gameId)
        if not failedGames[gid] or (currentTime - failedGames[gid] >= 300) then
            table.insert(workingIds, gameId)
        end
    end

    return #workingIds > 0 and workingIds or gameIds
end

local function joinRandomServerFromCurrentGame()
    cleanupOldServers()
    saveScriptData()
    queueScript()

    local currentGameId = tostring(game.PlaceId)
    local attempts = 0
    local maxAttempts = 15

    while attempts < maxAttempts and isRunning do
        local availableServers = getAvailableServers(currentGameId)

        if #availableServers > 0 then
            local selectedServer = selectBestServer(availableServers)

            if selectedServer then
                joinedServers[selectedServer.id] = tick()
                saveScriptData()

                if tryTeleportWithRetry(currentGameId, selectedServer.id) then
                    return
                end
            end
        end

        if attempts > 5 then
            local randomAttempt = math.random(1, 3)
            for i = 1, randomAttempt do
                if tryTeleportWithRetry(currentGameId, nil) then
                    return
                end
                wait(1)
            end
        end

        attempts = attempts + 1
        wait(2)
    end

    wait(math.random(3, 7))
    if isRunning then
        joinRandomServerFromCurrentGame()
    end
end

local function startSpamming()
    spawn(function()
        waitForGameLoad()

        if not isRunning then return end

        if not messagesSent then
            local selectedMessages = getRandomMessages()

            for i, message in ipairs(selectedMessages) do
                if not isRunning then break end
                pcall(function()
                    sendMessage(message) -- sanitized: prints only
                end)
                wait(math.random(0.5, 1.5))
            end

            messagesSent = true
            saveScriptData()
        end

        if isRunning then
            wait(2)
            joinRandomServerFromCurrentGame()
        end
    end)
end

local function stopSpamming()
    isRunning = false
    saveScriptData()
end

local function onKeyPress(input, gameProcessed)
    if gameProcessed then return end
    if input.KeyCode == Enum.KeyCode.Q then
        stopSpamming()
    elseif input.KeyCode == Enum.KeyCode.R then
        rejoinServer()
    end
end

local function initialize()
    loadScriptData()

    UserInputService.InputBegan:Connect(onKeyPress)

    if game.JobId and game.JobId ~= "" then
        joinedServers[game.JobId] = tick()
    end

    messagesSent = false

    startSpamming()
end

initialize()
