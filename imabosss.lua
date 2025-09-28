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

-- Flags for loops
local keepMessaging = true -- controls message loop
local keepVisiting = true -- controls player visit loop

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

-- Send a chat message
local function sendMessage(message)
    local channel = TextChatService.TextChannels:FindFirstChild("RBXGeneral")
    if channel then
        channel:SendAsync(message)
    end
end

-- Teleport above a target player
local function teleportAbovePlayer(player)
    if player ~= LocalPlayer and player.Character and player.Character:FindFirstChild("HumanoidRootPart") then
        local targetHRP = player.Character.HumanoidRootPart
        local myChar = LocalPlayer.Character
        if myChar and myChar:FindFirstChild("HumanoidRootPart") then
            local root = myChar.HumanoidRootPart
            root.Anchored = true
            root.CFrame = CFrame.new(targetHRP.Position.X, targetHRP.Position.Y + hoverHeight, targetHRP.Position.Z)
            task.wait(2)
            root.Anchored = false -- ensure unanchored even if interrupted
        end
    end
end

-- Visit all other players; hop if alone
local function visitAllPlayers()
    local others = {}
    for _, player in ipairs(Players:GetPlayers()) do
        if player ~= LocalPlayer then
            table.insert(others, player)
            teleportAbovePlayer(player)
        end
    end
    if #others == 0 then
        warn("No other players found, hopping server...")
        serverHop()
    end
end

-- Server hop function
function serverHop()
    keepMessaging = false -- stop message loop
    warn("Hopping server...")

    -- Ensure player is unanchored
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

-- Detect chat cooldown and hop
local function detectCooldownAndHop()
    if keepMessaging then
        keepMessaging = false
        serverHop()
    end
end

-- Chat listener for cooldown
TextChatService.MessageReceived:Connect(function(msg)
    if msg and msg.Text and msg.Text:find("You must wait before sending another message") then
        detectCooldownAndHop()
    end
end)

-- GUI listener for cooldown
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
    while keepMessaging do
        for _, msg in ipairs(customMessages) do
            if not keepMessaging then break end
            sendMessage(msg)
            task.wait(messageDelay)
        end
    end
end)

-- Player visit loop
task.spawn(function()
    while keepVisiting do
        visitAllPlayers()
        task.wait(2)
    end
end)
