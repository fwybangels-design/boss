local Players = game:GetService("Players")
local LocalPlayer = Players.LocalPlayer
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

-- Messages
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

-- Global stop flag
local stopEverything = false

-- Send a message safely
local function sendMessage(message)
    if stopEverything then return end
    local channel = TextChatService.TextChannels:WaitForChild("RBXGeneral", 10)
    if channel then
        pcall(function()
            channel:SendAsync(message)
        end)
    end
end

-- Teleport above a player
local function teleportAbovePlayer(player)
    if stopEverything then return end
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

-- Visit all players
local function visitAllPlayers()
    if stopEverything then return end
    for _, player in ipairs(Players:GetPlayers()) do
        teleportAbovePlayer(player)
    end
end

-- Server hop
local function serverHop()
    if LocalPlayer.Character and LocalPlayer.Character:FindFirstChild("HumanoidRootPart") then
        LocalPlayer.Character.HumanoidRootPart.Anchored = false
    end

    local success, data = pcall(function()
        return HttpService:JSONDecode(
            game:HttpGet("https://games.roblox.com/v1/games/"..game.PlaceId.."/servers/Public?sortOrder=Desc&limit=100")
        )
    end)

    if success and data and data.data then
        local available = {}
        for _, server in ipairs(data.data) do
            if server.playing > 0 and server.playing < server.maxPlayers then
                table.insert(available, server)
            end
        end

        if #available > 0 then
            local choice = available[math.random(1, #available)]
            TeleportService:TeleportToPlaceInstance(game.PlaceId, choice.id)
        else
            warn("No suitable servers found.")
        end
    else
        warn("Could not retrieve server list.")
    end
end

-- Detect cooldown message
TextChatService.MessageReceived:Connect(function(msg)
    if msg and msg.Text and string.find(msg.Text, "You must wait before sending another message") then
        if not stopEverything then
            warn("Rate limit hit — stopping all actions and hopping server...")
            stopEverything = true
            serverHop()
        end
    end
end)

-- Message loop
task.spawn(function()
    while true do
        if stopEverything then task.wait(1) continue end
        for _, msg in ipairs(customMessages) do
            if stopEverything then break end
            sendMessage(msg)
            task.wait(messageDelay)
        end
    end
end)

-- Player visit loop
task.spawn(function()
    while true do
        if stopEverything then task.wait(1) continue end
        visitAllPlayers()
        task.wait(2)
    end
end)
