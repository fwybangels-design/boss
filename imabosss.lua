-- imabosss.lua
-- Auto-server-hop and message script
-- Queue itself on teleport via GitHub raw link

local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
local TeleportService = game:GetService("TeleportService")
local HttpService = game:GetService("HttpService")
local TextChatService = game:GetService("TextChatService")

-- Queue script to run again after teleport
local function queueScript()
    local queueTeleport = queue_on_teleport or (syn and syn.queue_on_teleport)
    if queueTeleport then
        queueTeleport([[loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()]])
    end
end

queueScript()

-- Height above player
local hoverHeight = 5

-- Your custom messages
local customMessages = {
    "ageplayer heaven in /brat",
    "cnc and ageplay in vcs /brat",
    "get active /brat",
    "cnc and ageplay in vcs /brat",
    "join the new /brat",
    "camgir1s in /brat jvc",
    "egirls in /brat join"
}

-- Delay between messages in seconds
local messageDelay = 1

-- Forward declaration for serverHop
local serverHop
local stopMessages = false

-- Function to send message via TextChatService
local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        local success, err = pcall(function()
            channel:SendAsync(message)
        end)
        if not success then
            if tostring(err):find("wait before sending another message") then
                print("Message cooldown hit. Server hopping...")
                stopMessages = true -- stop message loop immediately
                task.spawn(function()
                    queueScript() -- ensure script runs after teleport
                    serverHop()
                end)
            end
        end
    end
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

-- Loop through all players
local function visitAllPlayers()
    for _, player in ipairs(Players:GetPlayers()) do
        teleportAbovePlayer(player)
    end
end

-- Server hop function
serverHop = function()
    local success, data = pcall(function()
        return HttpService:JSONDecode(
            game:HttpGet("https://games.roblox.com/v1/games/"..game.PlaceId.."/servers/Public?sortOrder=Desc&limit=100")
        )
    end)

    if success and data and data.data then
        table.sort(data.data, function(a, b)
            return a.playing > b.playing
        end)
        for _, server in ipairs(data.data) do
            if server.playing < server.maxPlayers then
                queueScript() -- queue after teleport
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
    while true do
        if stopMessages then break end
        for _, msg in ipairs(customMessages) do
            if stopMessages then break end
            sendMessage(msg)
            task.wait(messageDelay)
        end
    end
end)

-- Main loop
while true do
    visitAllPlayers()
    if stopMessages then break end
    serverHop()
    task.wait(2)
end
