local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer

-- 🔧 Make RNG unique per account
math.randomseed(tick() + LocalPlayer.UserId)

-- RANDOMIZED STARTUP STAGGER (2–10s) — prevents multi-client collision at launch
task.wait(math.random(2, 10))

local TeleportService = game:GetService("TeleportService")
local HttpService = game:GetService("HttpService")
local TextChatService = game:GetService("TextChatService")

-- Queue script to run again after teleport from GitHub
local queueTeleport = queue_on_teleport or (syn and syn.queue_on_teleport)
if queueTeleport then
    queueTeleport([[
        loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/main/imabosss.lua"))()
    ]])
end

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

-- Function to send message via TextChatService
local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        channel:SendAsync(message)
    end
end

-- Teleport above a player for 2 seconds
local function teleportAbovePlayer(player)
    if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("HumanoidRootPart") then
        local targetHRP = player.Character.HumanoidRootPart
        local myChar = LocalPlayer.Character
        if myChar and myChar:FindFirstChild("HumanoidRootPart") then
            local root = myChar.HumanoidRootPart
            root.Anchored = true
            root.CFrame = CFrame.new(targetHRP.Position.X, targetHRP.Position.Y + hoverHeight, targetHRP.Position.Z)
            task.wait(2) -- hover 2 seconds above player
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

-- Server hop function: join a random open server
local function serverHop()
    -- tiny random delay to desync multiple accounts
    local rnd = Random.new(math.floor(tick() * 1000) + (LocalPlayer and LocalPlayer.UserId or 0))
    task.wait(rnd:NextNumber(0.5, 3.5))

    local success, data = pcall(function()
        return HttpService:JSONDecode(
            game:HttpGet("https://games.roblox.com/v1/games/"..game.PlaceId.."/servers/Public?sortOrder=Asc&limit=100")
        )
    end)

    if success and data and data.data then
        -- Filter out full servers
        local openServers = {}
        for _, server in ipairs(data.data) do
            if server.playing < server.maxPlayers then
                table.insert(openServers, server)
            end
        end

        if #openServers > 0 then
            -- pick a random open server
            local chosen = openServers[math.random(1, #openServers)]
            TeleportService:TeleportToPlaceInstance(game.PlaceId, chosen.id)
            return
        end
    else
        warn("Could not retrieve server list.")
    end

    -- fallback: normal teleport if no server found
    TeleportService:Teleport(game.PlaceId)
end

-- Detect "You must wait before sending another message"
TextChatService.MessageReceived:Connect(function(msg)
    if msg and msg.Text and string.find(msg.Text, "You must wait before sending another message") then
        warn("Rate limit hit — hopping server...")
        serverHop()
    end
end)

-- Run message loop separately with delay
task.spawn(function()
    while true do
        for _, msg in ipairs(customMessages) do
            sendMessage(msg)
            task.wait(messageDelay) -- 1 second delay between messages
        end
    end
end)

-- Main loop: teleport above players and server hop
while true do
    visitAllPlayers()
    serverHop()
    task.wait(2) -- small delay before next server hop
end
