-- imabosss.lua
-- Auto-server-hop and message script
-- Queue itself on teleport via GitHub raw link

local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local TeleportService = game:GetService("TeleportService")
local HttpService = game:GetService("HttpService")
local TextChatService = game:GetService("TextChatService")

-- Queue script to run again after teleport
local queueTeleport = queue_on_teleport or (syn and syn.queue_on_teleport)
if queueTeleport then
    queueTeleport([[
        loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()
    ]])
end

local hoverHeight = 5
local customMessages = {
    "ageplayer heaven in /brat",
    "cnc and ageplay in vcs /brat",
    "get active /brat",
    "cnc and ageplay in vcs /brat",
    "join the new /brat",
    "camgir1s in /brat jvc",
    "egirls in /brat join"
}
local messageDelay = 1
local serverHop
local isRunning = true

-- Function to send message and detect cooldown
local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        pcall(function()
            channel:SendAsync(message)
        end)

        -- Check for system message immediately
        task.wait(0.2)
        for _, msg in ipairs(channel:GetChildren()) do
            if msg:IsA("Message") and msg.Text:lower():find("you must wait before sending another message") then
                print("Message cooldown detected. Server hopping...")
                isRunning = false
                serverHop()
                return true -- signal that cooldown happened
            end
        end
    end
    return false
end

-- Teleport above a player
local function teleportAbovePlayer(player)
    if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("HumanoidRootPart") then
        local targetHRP = player.Character.HumanoidRootPart
        local myChar = LocalPlayer.Character
        if myChar and myChar:FindFirstChild("HumanoidRootPart") then
            local root = myChar.HumanoidRootPart
            root.Anchored = true
            root.CFrame = CFrame.new(targetHRP.Position.X, targetHRP.Position.Y + hoverHeight, targetHRP.Position.Z)
            task.wait(2)
            root.Anchored = false
        end
    end
end

local function visitAllPlayers()
    for _, player in ipairs(Players:GetPlayers()) do
        if not isRunning then break end
        teleportAbovePlayer(player)
    end
end

serverHop = function()
    local success, data = pcall(function()
        return HttpService:JSONDecode(
            game:HttpGet("https://games.roblox.com/v1/games/"..game.PlaceId.."/servers/Public?sortOrder=Desc&limit=100")
        )
    end)

    if success and data and data.data then
        table.sort(data.data, function(a, b) return a.playing > b.playing end)
        for _, server in ipairs(data.data) do
            if server.playing < server.maxPlayers then
                TeleportService:TeleportToPlaceInstance(game.PlaceId, server.id)
                return
            end
        end
    else
        warn("Could not retrieve server list.")
    end
end

-- Run message loop
task.spawn(function()
    while isRunning do
        for _, msg in ipairs(customMessages) do
            if not isRunning then break end
            local cooldownDetected = sendMessage(msg)
            if cooldownDetected then break end -- immediately stop sending further messages
            task.wait(messageDelay)
        end
    end
end)

-- Main loop: teleport above players
while isRunning do
    visitAllPlayers()
    task.wait(2)
end
