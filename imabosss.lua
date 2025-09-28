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

-- Delay
local messageDelay = 1
local keepMessaging = true -- control flag

local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        channel:SendAsync(message)
    end
end

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
        teleportAbovePlayer(player)
    end
end

local function serverHop()
    keepMessaging = false -- stop message loop instantly
    warn("Rate limit hit — hopping server...")

    local success, data = pcall(function()
        return HttpService:JSONDecode(
            game:HttpGet("https://games.roblox.com/v1/games/"..game.PlaceId.."/servers/Public?sortOrder=Desc&limit=100")
        )
    end)

    if success and data and data.data then
        local available = {}
        for _, server in ipairs(data.data) do
            if server.playing < server.maxPlayers then
                table.insert(available, server)
            end
        end

        if #available > 0 then
            local choice = available[math.random(1, #available)]
            TeleportService:TeleportToPlaceInstance(game.PlaceId, choice.id)
            return
        end
    else
        warn("Could not retrieve server list.")
    end
end

-- Cooldown detection
local function detectCooldownAndHop()
    if keepMessaging then
        keepMessaging = false
        serverHop()
    end
end

TextChatService.MessageReceived:Connect(function(msg)
    if msg and msg.Text and msg.Text:find("You must wait before sending another message") then
        detectCooldownAndHop()
    end
end)

LocalPlayer.PlayerGui.ChildAdded:Connect(function(child)
    if child:IsA("ScreenGui") and child.Name == "Chat" then
        child.DescendantAdded:Connect(function(desc)
            if desc:IsA("TextLabel") and desc.Text:find("You must wait before sending another message") then
                detectCooldownAndHop()
            end
        end)
    end
end)

-- Message loop
task.spawn(function()
    while true do
        if not keepMessaging then break end
        for _, msg in ipairs(customMessages) do
            if not keepMessaging then break end
            sendMessage(msg)
            task.wait(messageDelay)
        end
    end
end)

-- Main loop
while true do
    if not keepMessaging then break end
    visitAllPlayers()
    task.wait(2)
end
