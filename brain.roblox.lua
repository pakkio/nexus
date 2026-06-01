-- NPC Brain for Roblox. Model name "NPCName.AreaName", set attribute "ServerURL"
local Players, HttpService, Chat = game:GetService("Players"), game:GetService("HttpService"), game:GetService("Chat")
local model, DEBUG = script.Parent, false
local rootPart = model:FindFirstChild("HumanoidRootPart")
	or (model:IsA("Model") and model.PrimaryPart or nil)
	or model:FindFirstChildWhichIsA("BasePart")
local humanoid = model:FindFirstChildOfClass("Humanoid")
local SERVER_URL = model:GetAttribute("ServerURL") or ""
local TIMEOUT = 300
local R,W,G,Y,B = Color3.new(1,0,0), Color3.new(1,1,1), Color3.new(0,1,0), Color3.new(1,1,0), Color3.new(0.3,0.7,1)
local isConversing, currentPlayer, convTimer, listenConn, billboardGui = false, nil, nil, nil, nil
local NPC_NAME, CURRENT_AREA = "", ""
local endConversation, resetTimeout

-- Billboard label
local function setLabel(text, color)
	if not billboardGui then
		local gui = Instance.new("BillboardGui")
		gui.Name, gui.Size, gui.StudsOffset, gui.AlwaysOnTop = "StatusBillboard", UDim2.new(0,220,0,70), Vector3.new(0,3.5,0), true
		gui.Parent = rootPart or model:FindFirstChildWhichIsA("BasePart") or (model:IsA("BasePart") and model or nil) or model
		local l = Instance.new("TextLabel")
		l.Name, l.Size, l.BackgroundTransparency, l.TextColor3, l.TextScaled, l.TextWrapped = "Label", UDim2.fromScale(1,1), 1, W, true, true
		l.Font = Enum.Font.GothamBold; l.Parent = gui
		billboardGui = gui
	end
	local l = billboardGui:FindFirstChild("Label")
	if l then l.Text, l.TextColor3 = text, color end
end

local function setColor(color)
	for _, part in model:GetDescendants() do
		if part:IsA("BasePart") and part.Name ~= "HumanoidRootPart" then part.Color = color end
	end
end

-- Speech
local function npcSay(msg)
	local part = rootPart or model:FindFirstChildWhichIsA("BasePart") or (model:IsA("BasePart") and model or nil)
	if part then Chat:Chat(part, msg, Enum.ChatColor.Blue) end
	if DEBUG then print("[" .. NPC_NAME .. "] " .. msg) end
end

local function ownerSay(msg) print("[NPC] " .. msg) end
local function errSay(msg) warn("[NPC-ERROR] " .. msg) end

-- Wrap callbacks to catch and log crashes
local function try(f, ...)
	local args = {...}
	return xpcall(function() f(table.unpack(args)) end, function(e) errSay(tostring(e) .. "\n" .. debug.traceback()) end)
end

-- JSON helpers
local function escapeJSON(s)
	return s:gsub("\\","\\\\"):gsub('"','\\"'):gsub("\n","\\n"):gsub("\r","\\r"):gsub("\t","\\t")
end

local function extractJSON(body, key)
	local val = body:match('"' .. key .. '":%s*"(.-[^\\])"') or body:match('"' .. key .. '":%s*"()"')
	if val then return val:gsub('\\"','"'):gsub("\\n","\n"):gsub("\\\\","\\") end
	return body:match('"' .. key .. '":%s*([%w%.%-]+)') or ""
end

-- HTTP
local function req(method, endpoint, data)
	local opts = {Url = SERVER_URL .. endpoint, Method = method}
	if data then opts.Headers = {["Content-Type"] = "application/json"}; opts.Body = data end
	local ok, res = pcall(HttpService.RequestAsync, HttpService, opts)
	if ok then return true, res.Body, res.StatusCode end
	return false, tostring(res), 0
end

-- Animations
local animTracks = {}

local function playAnim(name)
	if not humanoid then return end
	name = name:match("^%s*(.-)%s*$")
	local obj = model:FindFirstChild(name)
	if not obj or not obj:IsA("Animation") then
		if DEBUG then ownerSay("Animation not found: " .. name) end; return
	end
	if animTracks[name] then animTracks[name]:Stop() end
	local track = humanoid:LoadAnimation(obj); track:Play(); animTracks[name] = track
end

-- SL commands
local function processSLCommands(sl)
	for key, value in sl:gmatch("([%w]+)=([^;%]]+)") do
		local k = key:lower()
		if k == "anim" or k == "emote" then playAnim(value)
		elseif k == "llsettext" then setLabel(value, W)
		elseif DEBUG then ownerSay(k .. " command (no-op in Roblox): " .. value) end
	end
end

-- Safe task spawn with error logging
local function spawn(f)
	task.spawn(function()
		local ok, e = pcall(f)
		if not ok then errSay(tostring(e)) end
	end)
end

-- Response handling
local function handleChatResponse(body)
	setColor(W); resetTimeout()
	local npcResp = extractJSON(body, "npc_response")
	if npcResp == "" then errSay("npc_response empty"); return end

	local anim = npcResp:match("%[anim=([^%]]+)%]")
	if anim then playAnim(anim) end

	local sl = extractJSON(body, "sl_commands")
	if sl ~= "" then processSLCommands(sl) end

	npcResp = npcResp:gsub("%[%a+=[^%]]*%]", ""):match("^%s*(.-)%s*$")
	if npcResp ~= "" then npcSay(npcResp)
	else errSay("cleaned response empty") end
end

-- Conversation
resetTimeout = function()
	if convTimer then task.cancel(convTimer); convTimer = nil end
	if not isConversing then return end
	convTimer = task.delay(TIMEOUT, function()
		if isConversing then ownerSay("Timeout ending conversation"); endConversation(true) end
	end)
end

endConversation = function(sayGoodbye)
	if not isConversing then return end
	local pn = currentPlayer and currentPlayer.Name or ""
	local data = string.format('{"player_name":"%s","npc_name":"%s","area":"%s","action":"leaving","message":"Avatar leaving","status":"end"}',
		escapeJSON(pn), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA))
	spawn(function() req("POST", "/api/leave_npc", data) end)
	if convTimer then task.cancel(convTimer); convTimer = nil end
	if listenConn then listenConn:Disconnect(); listenConn = nil end
	if sayGoodbye and pn ~= "" then npcSay("È stato un piacere parlare con te, " .. pn .. "!") end
	setColor(W); currentPlayer = nil; isConversing = false
	setLabel("Touch to talk to\n" .. NPC_NAME, G)
end

local function sendMessage(msg)
	if not isConversing then errSay("sendMessage called while not conversing"); return end
	setColor(R); resetTimeout()
	local data = string.format('{"message":"%s","player_name":"%s","npc_name":"%s","area":"%s"}',
		escapeJSON(msg), escapeJSON(currentPlayer.Name), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA))
	spawn(function()
		local ok, body, status = req("POST", "/api/chat", data)
		if ok and status == 200 then handleChatResponse(body)
		else setColor(W)
			errSay("HTTP error " .. tostring(status) .. ": " .. (body and body:sub(1,200) or "nil"))
			npcSay("Scusa, non posso risponderti ora.")
		end
	end)
end

local function startConversation(player)
	if isConversing then return end
	currentPlayer = player; isConversing = true
	setLabel("Conversing with\n" .. player.Name, B)
	local data = string.format('{"name":"%s","npcname":"%s","area":"%s"}',
		escapeJSON(player.Name), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA))
	spawn(function()
		local ok, body, status = req("POST", "/sense", data)
		if ok and status == 200 then
			handleChatResponse(body); resetTimeout()
			listenConn = player.Chatted:Connect(function(m) try(sendMessage, m) end)
		else
			isConversing = false; currentPlayer = nil
			setLabel("Touch to talk to\n" .. NPC_NAME, G)
			errSay("/sense failed for " .. player.Name .. " (status " .. tostring(status) .. ")")
		end
	end)
end

-- Parsing NPC name from model
NPC_NAME, CURRENT_AREA = "", ""
local dot = model.Name:find("%.")
if dot and dot > 1 then
	NPC_NAME = model.Name:sub(1, dot - 1)
	CURRENT_AREA = model.Name:sub(dot + 1)
end

-- Init
local function init()
	if SERVER_URL == "" or not SERVER_URL:match("^https?://") then
		setLabel("ERROR: ServerURL\nattribute not set", R)
		errSay("Set ServerURL attribute on Model"); return
	end
	if NPC_NAME == "" or CURRENT_AREA == "" then
		errSay("Model must be named 'NPCName.AreaName'")
		setLabel("ERROR: Invalid\nmodel name", R); return
	end
	ownerSay("NPC: " .. NPC_NAME .. " | Area: " .. CURRENT_AREA .. " | Server: " .. SERVER_URL)
	setLabel("Verifying\n" .. NPC_NAME .. "...", Y)
	spawn(function()
		local ok, body, status = req("GET", "/health")
		if not ok or status ~= 200 then
			setLabel("Server offline\n" .. NPC_NAME, R)
			errSay("Server not reachable (status " .. tostring(status) .. ")"); return
		end
		local vok, vbody, vstatus = req("POST", "/api/npc/verify",
			string.format('{"npc_name":"%s","area":"%s"}', escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA)))
		if vok and vstatus == 200 then
			if extractJSON(vbody, "found") == "true" then
				local caps = ""
				if extractJSON(vbody, "has_teleport") == "true" then caps = caps .. "TP|" end
				if extractJSON(vbody, "has_llsettext") == "true" then caps = caps .. "TXT|" end
				if extractJSON(vbody, "has_notecard") == "true" then caps = caps .. "NC" end
				setLabel("Touch to talk to\n" .. NPC_NAME .. "\n[" .. caps .. "]", G)
				ownerSay("NPC verified! Click to talk.")
			else setLabel("NPC not found\n" .. NPC_NAME, R); errSay("NPC '" .. NPC_NAME .. "' not found!") end
		else setLabel("Verify failed\n" .. NPC_NAME, R); errSay("Verify request failed (status " .. tostring(vstatus) .. ")") end
	end)
end

-- ClickDetector
local cd = model:FindFirstChildOfClass("ClickDetector")
if not cd then cd = Instance.new("ClickDetector"); cd.MaxActivationDistance = 10; cd.Parent = rootPart or model end
cd.MouseClick:Connect(function(player)
	try(function()
		if isConversing and currentPlayer == player then endConversation(true); return end
		if isConversing then return end
		startConversation(player)
	end)
end)

Players.PlayerRemoving:Connect(function(player)
	if isConversing and currentPlayer == player then endConversation(false) end
end)

init()
