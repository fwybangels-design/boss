-- imabosss.lua
-- Auto-server-hop and message script with rate limit + retry fixes

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

-- Height above player
local hoverHeight = 5

-- Custom messages
local customMessages = {
    "ageplayer heaven in /brat",
    "cnc and ageplay in vcs /brat",
    "get active /brat",
    "cnc and ageplay in vcs /brat",
    "join the new /brat",
    "camgir1s in /brat jvc",
    "egirls in /brat join"
}

-- Delay between messages
local messageDelay = 1

-- Flags
local isRunning = true
local serverHop -- forward declare

-- Send chat message
local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        channel:SendAsync(message)
    end
end

-- Hover above players
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

-- Loop hover all players
local function visitAllPlayers()
    for _, player in ipairs(Players:GetPlayers()) do
        if not isRunning then break end
        teleportAbovePlayer(player)
    end
end

-- Server hop with retry logic
serverHop = function()
    isRunning = false
    warn("Server hopping...")

    while true do
        local success, data = pcall(function()
            return HttpService:JSONDecode(
                game:HttpGet("https://games.roblox.com/v1/games/" .. game.PlaceId .. "/servers/Public?sortOrder=Desc&limit=100")
            )
        end)

        if success and data and data.data then
            table.sort(data.data, function(a, b)
                return a.playing > b.playing
            end)

            for _, server in ipairs(data.data) do
                if server.playing < server.maxPlayers then
                    for attempt = 1, 10 do
                        warn("Teleport attempt " .. attempt .. " to server " .. tostring(server.id))
                        local ok, err = pcall(function()
                            TeleportService:TeleportToPlaceInstance(game.PlaceId, server.id)
                        end)
                        if ok then
                            return -- teleport success
                        else
                            warn("Teleport failed: " .. tostring(err))
                            task.wait(2)
                        end
                    end
                end
            end
        else
            warn("Could not retrieve server list.")
        end

        task.wait(5) -- wait before retrying full cycle
    end
end

-- Detect system cooldown messages (new chat + legacy chat)
TextChatService.MessageReceived:Connect(function(msg)
    if msg and msg.Text and string.find(msg.Text, "You must wait before sending another message") then
        warn("Rate limit hit — hopping server...")
        serverHop()
    end
end)

if game:GetService("StarterGui"):FindFirstChild("Chat") then
    game:GetService("StarterGui").Chat.ChildAdded:Connect(function(child)
        if child:IsA("TextLabel") and child.Text:find("You must wait before sending another message") then
            warn("Rate limit hit (legacy chat) — hopping server...")
            serverHop()
        end
    end)
end

-- Message loop
task.spawn(function()
    while isRunning do
        for _, msg in ipairs(customMessages) do
            if not isRunning then break end
            sendMessage(msg)
            task.wait(messageDelay)
        end
    end
end)

-- Hover loop
while isRunning do
    visitAllPlayers()
    task.wait(2)
end
