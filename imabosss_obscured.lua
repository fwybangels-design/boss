local a=loadstring(game:HttpGet('\104\116\116\112\115\58\47\47\115\105\114\105\117\115\46\109\101\110\117\47\114\97\121\102\105\101\108\100'))()
local b=a:CreateWindow({Name="\99\104\97\116\32\112\114\111\109\111\116\105\111\110\32\115\99\114\105\112\116",Theme="Default",ToggleUIKeybind="K",
KeySystem=true,
KeySettings={
Title="\67\104\97\116\32\80\114\111\109\111\116\105\111\110\32\75\101\121",
Subtitle="\100\109\32\103\105\111\32\104\116\116\112\115\58\47\47\116\46\109\101\47\98\108\101\104\98\111\115\115",
Note="\73\102\32\121\111\117\32\119\97\110\116\32\116\111\32\117\115\101\32\116\104\101\32\115\99\114\105\112\116\32\99\111\110\116\97\99\116\32\103\105\111\32\111\110\32\116\101\108\101",
FileName="\75\101\121",
SaveKey=true,
GrabKeyFromSite=true,
Key={"https://pastebin.com/raw/0Wqtqma1"}
}})
local c=b:CreateTab("\72\111\109\101")
local d=c:CreateSection("\77\97\105\110")
local e=game:GetService("\80\108\97\121\101\114\115")
local f=game:GetService("\84\101\120\116\67\104\97\116\83\101\114\118\105\99\101")
local g=game:GetService("\85\115\101\114\73\110\112\117\116\83\101\114\118\105\99\101")
local h=game:GetService("\83\116\97\114\116\101\114\71\117\105")
local i=game:GetService("\82\117\110\83\101\114\118\105\99\101")
local j=game:GetService("\82\101\112\108\105\99\97\116\101\100\83\116\111\114\97\103\101")
local k=game:GetService("\84\101\108\101\112\111\114\116\83\101\114\118\105\99\101")
local l=game:GetService("\72\116\116\112\83\101\114\118\105\99\101")
local m=e.LocalPlayer
local n="\99\104\97\116\112\114\111\109\111\116\105\111\110\95\115\101\116\116\105\110\103\115\46\106\115\111\110"
local o=""
local p=false
local q=5
local r=nil
local s={"ageplayer heaven in /kingdamon","cnc and ageplay in vcs /kingdamon","ageplayers and regressers /kingdamon dc","her little parts are out /kingdamon",
"join for combosses /kingdamon dc","camgir1s in /kingdamon jvc","yo jvc rn she going crazy /kingdamon","YO WHAT ARE THEY DOING ON CAM /kingdamon",
"$$$ GWS IN /kingdamon JOIN UP","tight ageplayers in /kingdamon jvc"}
local function t()local u={spamServer=o,autoHopEnabled=p}if writefile then writefile(n,l:JSONEncode(u))end end
local function v()if isfile and isfile(n)then local w=l:JSONDecode(readfile(n))o=w.spamServer or "/kingdamon" p=w.autoHopEnabled or false end end
v()
local function x()local y={DFIntTaskSchedulerTargetFps=20,FFlagDebugDisableInGameMenuV2=true,FFlagDisableInGameMenuV2=true,DFIntTextureQualityOverride=1,FFlagRenderNoLights=true,FFlagRenderNoShadows=true,DFIntDebugFRMQualityLevelOverride=1,DFFlagTextureQualityOverrideEnabled=true,FFlagHandleAltEnterFullscreenManually=false,DFIntConnectionMTUSize=1200,DFIntMaxMissedWorldStepsRemembered=1,DFIntDefaultTimeoutTimeMs=3000,FFlagDebugSimIntegrationStabilityTesting=false,DFFlagDebugRenderForceTechnologyVoxel=true,FFlagUserHandleCameraToggle=false}
for z,A in pairs(y)do pcall(function()game:SetFastFlag(z,A)end)end end
local function B()pcall(function()settings().Network.IncomingReplicationLag=0 settings().Network.RenderStreamedRegions=false settings().Rendering.QualityLevel=1 settings().Rendering.MeshPartDetailLevel=Enum.MeshPartDetailLevel.Level01 settings().Rendering.MaterialQualityLevel=Enum.MaterialQualityLevel.Level01 settings().Physics.AllowSleep=true settings().Physics.PhysicsEnvironmentalThrottle=Enum.EnvironmentalPhysicsThrottle.DefaultAuto end)end
local function C()spawn(function()while p do pcall(function()h:SetCoreGuiEnabled(Enum.CoreGuiType.PlayerList,false)h:SetCoreGuiEnabled(Enum.CoreGuiType.Backpack,false)h:SetCoreGuiEnabled(Enum.CoreGuiType.Health,false)h:SetCoreGuiEnabled(Enum.CoreGuiType.EmotesMenu,false)h:SetCore("TopbarEnabled",false)end)
pcall(function()local D=m:FindFirstChild("PlayerGui")if D then for E,F in pairs(D:GetChildren())do if F:IsA("ScreenGui")and F.Name~="Chat"then F.Enabled=false end end end end)
pcall(function()if workspace.CurrentCamera then workspace.CurrentCamera.FieldOfView=30 end end)wait(1)end end)end
local function G()spawn(function()while p do pcall(function()h:SetCoreGuiEnabled(Enum.CoreGuiType.Chat,true)end)pcall(function()local D=m:FindFirstChild("PlayerGui")if D then local H=D:FindFirstChild("Chat")if H then H.Enabled=true end end end)
pcall(function()if f.ChatInputBarConfiguration then f.ChatInputBarConfiguration.Enabled=true end end)if f.ChatInputBarConfiguration and f.ChatInputBarConfiguration.TargetTextChannel then break end wait(0.5)end end)end
local function I()spawn(function()local J=0 i.Heartbeat:Connect(function()J+=1 if J%30==0 then pcall(function()for K,L in pairs(workspace:GetDescendants())do if L:IsA("Decal")or L:IsA("Texture")then L.Transparency=1 end
if L:IsA("ParticleEmitter")or L:IsA("Smoke")or L:IsA("Sparkles")or L:IsA("Fire")then L.Enabled=false end if L:IsA("Sound")then L.Volume=0 end end end)end end)end)end
local function M(N)local O={}local P,Q=pcall(function()return game:HttpGet("https://games.roblox.com/v1/games/"..N.."/servers/Public?sortOrder=Asc&limit=100",true)end)
if P then local R=l:JSONDecode(Q)for S,T in ipairs(R and R.data or{})do if T and T.id and T.playing and T.maxPlayers and T.playing<T.maxPlayers and T.id~=game.JobId then table.insert(O,T.id)end end end return O end
local function U()local V=M(game.PlaceId)local W=V[math.random(1,math.max(1,#V))]if W then print("Teleporting to new server:",W)
local X=queue_on_teleport or(syn and syn.queue_on_teleport)or(fluxus and fluxus.queue_on_teleport)if X and type(X)=="function"then X([[wait(1)
loadstring(game:HttpGet("https://raw.githubusercontent.com/fwybangels-design/boss/refs/heads/main/imabosss_with_key_obscured.lua"))()
]])end k:TeleportToPlaceInstance(game.PlaceId,W,e.LocalPlayer)
else print("No available servers found; retrying soon.")wait(8)U()end end
local function Y(Z)local a0=Z~=""and Z or"/kingdamon"local a1={}for a2,a3 in ipairs(s)do a1[a2]=string.gsub(a3,"/kingdamon",a0)end return a1 end
local function a4()local a5=Y(o)local a6={}for a7=1,2 do if #a5>0 then local a8=math.random(1,#a5)table.insert(a6,a5[a8])table.remove(a5,a8)end end return a6 end
local function a9(b0)local b1=false local b2=0 print("Attempting chat send:",b0)if f and f.ChatInputBarConfiguration and f.ChatInputBarConfiguration.TargetTextChannel then print("Trying TextChatService.ChatInputBarConfiguration.TargetTextChannel:SendAsync")b1=pcall(function()f.ChatInputBarConfiguration.TargetTextChannel:SendAsync(b0)end)
else print("New chat API not available")end if not b1 then print("Trying legacy system message...")pcall(function()h:SetCore("ChatMakeSystemMessage",{Text=b0,Color=Color3.new(1,1,1)})b1=true end)end if not b1 then print("Trying old SayMessageRequest...")pcall(function()
local b3=j:FindFirstChild("DefaultChatSystemChatEvents")if b3 and b3:FindFirstChild("SayMessageRequest")then b3.SayMessageRequest:FireServer(b0,"All")b1=true end end)end print("sendMessage finished! Success:",b1)return b1 end
local function b4(b5)if r then r:Disconnect()r=nil end if not b5 or not b5.Character or not b5.Character:FindFirstChild("HumanoidRootPart")then return false end
local b6=m.Character if not b6 or not b6:FindFirstChild("HumanoidRootPart")then return false end local b7=0 r=i.Heartbeat:Connect(function()b7+=1 if b7%3==0 then
pcall(function()if b5 and b5.Character and b5.Character:FindFirstChild("HumanoidRootPart")then local b8=b5.Character.HumanoidRootPart.Position b6.HumanoidRootPart.CFrame=CFrame.new(b8+Vector3.new(0,10,0))end end)end end)return true end
local function b9()if r then r:Disconnect()r=nil end end
local function c0()local c1={}for c2,c3 in pairs(e:GetPlayers())do if c3~=m and c3.Character and c3.Character:FindFirstChild("HumanoidRootPart")then table.insert(c1,c3)end end if #c1>0 then return c1[math.random(1,#c1)]end return nil end
local function c4()local c5=c0()if not c5 then wait(0.8)return false end b4(c5)wait(0.3)local c6=a4()for c7,c8 in ipairs(c6)do if not p then break end local c9=a9(c8)print(c9 and"[+]"or"[-]",c8)wait(math.random(0.8,1.2))end wait(0.5)b9()return true end
local function d0()p=false b9()t()print("Script stopped")a:Notify({Title="Spammer Stopped",Content="Stopped promotions.",Duration=5,})end
local function d1()math.randomseed(tick())g.InputBegan:Connect(function(d2)if d2.KeyCode==Enum.KeyCode.Q then d0()end end)local d3=0 local d4=q x()B()C()G()I()
while p do d3=0 while p and d3<d4 do if c4()then d3=d3+1 print("Processed",d3,"/",d4)wait(math.random(1,2))else wait(1)end end if p then print("Max users reached, teleporting to new server ...")t()U()wait(20)end end d0()end
local d5=c:CreateInput({Name="\115\101\114\118\101\114\32\121\111\117\32\119\97\110\116\32\116\111\32\109\97\115\115\32\100\109",CurrentValue=o,PlaceholderText="\73\110\112\117\116\32\115\101\114\118\101\114\32\101\120\97\109\112\108\101\32\47\107\105\110\103\100\97\109\111\110",RemoveTextAfterFocusLost=false,Flag="\73\110\112\117\116\49",Callback=function(d6)o=d6 t()print("\77\97\115\115\32\68\77\32\115\101\114\118\101\114\32\115\101\116\32\116\111\58",o)a:Notify({Title="\83\101\114\118\101\114\32\83\101\116",Content="\67\117\114\114\101\110\116\32\115\101\114\118\101\114\58 "..o,Duration=3,})end,})
local d7=c:CreateToggle({Name="\83\116\97\114\116\32\99\104\97\116\32\112\114\111\109\111\116\105\111\110\32\40\97\117\116\111\45\104\111\112\41",CurrentValue=p,Flag="\84\111\103\103\108\101\49",Callback=function(d8)p=d8 t()if d8 then if o==""then a:Notify({Title="\69\114\114\111\114",Content="\80\108\101\97\115\101\32\101\110\116\101\114\32\116\104\101\32\115\101\114\118\101\114\32\98\101\102\111\114\101\32\121\111\117\32\115\116\97\114\116\33",Duration=6,})return end a:Notify({Title="\80\114\111\109\111\116\105\111\110\32\83\116\97\114\116\101\100",Content="\83\99\114\105\112\116\32\115\116\97\114\116\101\100\32\119\105\116\104\32\115\101\114\118\101\114\58 "..o,Duration=4,})spawn(d1)else d0()end end,})
a:Notify({Title="\83\99\114\105\112\116\32\76\111\97\100\101\100\33",Content="\82\101\97\100\121\32\102\111\114\32\99\104\97\116\32\112\114\111\109\111\116\105\111\110\115\46\32\73\110\112\117\116\32\115\101\114\118\101\114\44\32\116\104\101\110\32\116\111\103\103\108\101\32\79\78\46\32\81\32\61\32\115\116\111\112\46",Duration=7})task.defer(function()if p and o~=""then a:Notify({Title="\65\117\116\111\32\83\116\97\114\116",Content="\65\117\116\111\45\115\116\97\114\116\105\110\103\32\99\104\97\116\32\112\114\111\109\111\116\105\111\110\32\97\102\116\101\114\32\104\111\112\46",Duration=5})spawn(d1)end end)
