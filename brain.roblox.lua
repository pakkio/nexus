-- BRAIN.ROBLOX.LUA - AI-Driven NPC Brain for Roblox
-- Analogous to brain.lsl (Second Life). Place as a Script inside an NPC Model.
-- Model name format: "NPCName.AreaName"
-- Set a StringAttribute "ServerURL" on the Model to your Nexus server URL.
--
-- Required model structure:
--   Model (named "NPCName.AreaName", with StringAttribute ServerURL)
--     HumanoidRootPart (or any BasePart as primary)
--     Humanoid
--     ClickDetector (auto-created if missing)
--     Animation objects (optional, named to match anim= commands)

local Players     = game:GetService("Players")
local HttpService = game:GetService("HttpService")
local Chat        = game:GetService("Chat")

-- ============================================
-- CONFIGURATION
-- ============================================

local DEBUG = false

local model    = script.Parent
local rootPart = model:FindFirstChild("HumanoidRootPart")
              or (model:IsA("Model") and model.PrimaryPart or nil)
              or model:FindFirstChildWhichIsA("BasePart")
local humanoid = model:FindFirstChildOfClass("Humanoid")

local SERVER_URL  = model:GetAttribute("ServerURL") or ""
local NPC_NAME    = ""
local CURRENT_AREA = ""
local TIMEOUT     = 300 -- seconds

-- ============================================
-- COLORS
-- ============================================

local RED    = Color3.new(1, 0, 0)
local WHITE  = Color3.new(1, 1, 1)
local GREEN  = Color3.new(0, 1, 0)
local YELLOW = Color3.new(1, 1, 0)
local BLUE   = Color3.new(0.3, 0.7, 1)

-- ============================================
-- STATE (forward-declared so functions can cross-reference)
-- ============================================

local isConversing       = false
local currentPlayer: Player? = nil
local conversationTimer: thread? = nil
local listenConnection: RBXScriptConnection? = nil
local billboardGui: BillboardGui? = nil

-- Forward declarations
local endConversation: (boolean) -> ()
local resetConversationTimeout: () -> ()

-- ============================================
-- BILLBOARD LABEL
-- ============================================

local function setLabel(text: string, color: Color3)
	if not billboardGui then
		local gui = Instance.new("BillboardGui")
		gui.Name = "StatusBillboard"
		gui.Size = UDim2.new(0, 220, 0, 70)
		gui.StudsOffset = Vector3.new(0, 3.5, 0)
		gui.AlwaysOnTop = true
		gui.Parent = rootPart
		          or model:FindFirstChildWhichIsA("BasePart")
		          or (model:IsA("BasePart") and model or nil)
		          or model

		local label = Instance.new("TextLabel")
		label.Name = "Label"
		label.Size = UDim2.fromScale(1, 1)
		label.BackgroundTransparency = 1
		label.TextColor3 = WHITE
		label.TextScaled = true
		label.TextWrapped = true
		label.Font = Enum.Font.GothamBold
		label.Parent = gui

		billboardGui = gui
	end

	local label = billboardGui:FindFirstChild("Label") :: TextLabel?
	if label then
		label.Text = text
		label.TextColor3 = color
	end
end

-- ============================================
-- PART COLOR INDICATOR (like llSetColor in LSL)
-- ============================================

local function setColor(color: Color3)
	for _, part in model:GetDescendants() do
		if part:IsA("BasePart") and part.Name ~= "HumanoidRootPart" then
			part.Color = color
		end
	end
end

-- ============================================
-- NPC SPEECH
-- ============================================

local function npcSay(message: string)
	local part = rootPart
	          or model:FindFirstChildWhichIsA("BasePart")
	          or (model:IsA("BasePart") and model or nil)
	if part then
		Chat:Chat(part, message, Enum.ChatColor.Blue)
	end
	if DEBUG then print("[" .. NPC_NAME .. "] " .. message) end
end

local function ownerSay(message: string)
	print("[NPC:" .. NPC_NAME .. "] " .. message)
end

-- ============================================
-- JSON HELPERS
-- ============================================

local function escapeJSON(s: string): string
	s = s:gsub("\\", "\\\\")
	s = s:gsub('"',  '\\"')
	s = s:gsub("\n", "\\n")
	s = s:gsub("\r", "\\r")
	s = s:gsub("\t", "\\t")
	return s
end

-- Minimal flat-JSON key extractor (handles string values only)
local function extractJSON(body: string, key: string): string
	-- Match "key": "value" allowing escaped quotes inside value
	local val = body:match('"' .. key .. '":%s*"(.-[^\\])"')
	          or body:match('"' .. key .. '":%s*"()"')  -- empty string
	if val then
		val = val:gsub('\\"', '"')
		val = val:gsub("\\n", "\n")
		val = val:gsub("\\\\", "\\")
	end
	-- Also handle boolean/number values (returned as-is without quotes)
	if not val then
		val = body:match('"' .. key .. '":%s*([%w%.%-]+)')
	end
	return val or ""
end

-- ============================================
-- ANIMATIONS
-- ============================================

local animTracks: { [string]: AnimationTrack } = {}

local function playAnim(animName: string)
	if not humanoid then return end
	animName = animName:match("^%s*(.-)%s*$") -- trim whitespace

	local animObj = model:FindFirstChild(animName)
	if not animObj or not animObj:IsA("Animation") then
		if DEBUG then ownerSay("Animation not found: " .. animName) end
		return
	end

	-- Stop previous track for this name if still playing
	if animTracks[animName] then
		animTracks[animName]:Stop()
	end

	local track = humanoid:LoadAnimation(animObj)
	track:Play()
	animTracks[animName] = track
end

-- ============================================
-- SL COMMAND PROCESSING
-- ============================================

local function processSLCommands(slCommands: string)
	-- Parse [key=value;key=value] style blocks from sl_commands field
	for key, value in slCommands:gmatch("([%w]+)=([^;%]]+)") do
		local k = key:lower()
		if k == "anim" or k == "emote" then
			playAnim(value)
		elseif k == "llsettext" then
			setLabel(value, WHITE)
		elseif k == "face" then
			if DEBUG then ownerSay("face command (no-op in Roblox): " .. value) end
		elseif k == "teleport" then
			if DEBUG then ownerSay("teleport command: " .. value) end
		elseif k == "lookup" then
			if DEBUG then ownerSay("lookup command: " .. value) end
		end
	end
end

-- ============================================
-- RESPONSE PARSING
-- ============================================

local function parseAnimations(text: string)
	local animName = text:match("%[anim=([^%]]+)%]")
	if animName then
		playAnim(animName)
	end
end

local function cleanText(text: string): string
	text = text:gsub("%[%a+=[^%]]*%]", "") -- strip [tag=value] blocks
	text = text:match("^%s*(.-)%s*$")       -- trim
	return text
end

local function handleChatResponse(body: string)
	setColor(WHITE)
	resetConversationTimeout()

	if DEBUG then
		ownerSay("=== RESPONSE RECEIVED === len=" .. #body)
	end

	local npcResponse = extractJSON(body, "npc_response")
	if npcResponse == "" then
		if DEBUG then ownerSay("ERROR: npc_response empty") end
		return
	end

	parseAnimations(npcResponse)

	local slCommands = extractJSON(body, "sl_commands")
	if slCommands ~= "" then
		processSLCommands(slCommands)
	end

	npcResponse = cleanText(npcResponse)
	if npcResponse ~= "" then
		npcSay(npcResponse)
	else
		if DEBUG then ownerSay("ERROR: cleaned response empty") end
	end
end

-- ============================================
-- HTTP HELPERS
-- ============================================

local function httpPost(endpoint: string, data: string): (boolean, string, number)
	local ok, result = pcall(HttpService.RequestAsync, HttpService, {
		Url     = SERVER_URL .. endpoint,
		Method  = "POST",
		Headers = { ["Content-Type"] = "application/json" },
		Body    = data,
	})
	if ok then
		return true, (result :: any).Body, (result :: any).StatusCode
	end
	return false, tostring(result), 0
end

local function httpGet(endpoint: string): (boolean, string, number)
	local ok, result = pcall(HttpService.RequestAsync, HttpService, {
		Url    = SERVER_URL .. endpoint,
		Method = "GET",
	})
	if ok then
		return true, (result :: any).Body, (result :: any).StatusCode
	end
	return false, tostring(result), 0
end

-- ============================================
-- CONVERSATION TIMEOUT
-- ============================================

resetConversationTimeout = function()
	if conversationTimer then
		task.cancel(conversationTimer)
		conversationTimer = nil
	end
	if not isConversing then return end
	conversationTimer = task.delay(TIMEOUT, function()
		if isConversing then
			ownerSay("Timeout: ending conversation with " .. (currentPlayer and currentPlayer.Name or "?"))
			endConversation(true)
		end
	end)
end

-- ============================================
-- CONVERSATION MANAGEMENT
-- ============================================

endConversation = function(sayGoodbye: boolean)
	if not isConversing then return end

	local playerName = currentPlayer and currentPlayer.Name or ""

	-- Notify server asynchronously
	local leaveData = string.format(
		'{"player_name":"%s","npc_name":"%s","area":"%s","action":"leaving","message":"Avatar leaving","status":"end"}',
		escapeJSON(playerName), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA)
	)
	task.spawn(function()
		httpPost("/api/leave_npc", leaveData)
	end)

	if conversationTimer then
		task.cancel(conversationTimer)
		conversationTimer = nil
	end
	if listenConnection then
		listenConnection:Disconnect()
		listenConnection = nil
	end

	if sayGoodbye and playerName ~= "" then
		npcSay("È stato un piacere parlare con te, " .. playerName .. "!")
	end

	setColor(WHITE)
	currentPlayer = nil
	isConversing  = false
	setLabel("Touch to talk to\n" .. NPC_NAME, GREEN)
end

local function sendMessage(msg: string, playerName: string)
	if not isConversing then
		if DEBUG then ownerSay("ERROR: Not conversing") end
		return
	end

	setColor(RED)
	resetConversationTimeout()

	local chatData = string.format(
		'{"message":"%s","player_name":"%s","npc_name":"%s","area":"%s"}',
		escapeJSON(msg), escapeJSON(playerName), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA)
	)

	if DEBUG then ownerSay("Sending /api/chat...") end

	task.spawn(function()
		local ok, body, status = httpPost("/api/chat", chatData)
		if ok and status == 200 then
			handleChatResponse(body)
		else
			setColor(WHITE)
			if DEBUG then
				ownerSay("HTTP error " .. tostring(status))
				ownerSay("Body: " .. body:sub(1, 200))
			end
			npcSay("Scusa, non posso risponderti ora.")
		end
	end)
end

local function startConversation(player: Player)
	if isConversing then return end

	currentPlayer = player
	isConversing  = true
	setLabel("Conversing with\n" .. player.Name, BLUE)

	local senseData = string.format(
		'{"name":"%s","npcname":"%s","area":"%s"}',
		escapeJSON(player.Name), escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA)
	)

	if DEBUG then ownerSay("Sending /sense for " .. player.Name) end

	task.spawn(function()
		local ok, body, status = httpPost("/sense", senseData)
		if ok and status == 200 then
			handleChatResponse(body)
			resetConversationTimeout()

			-- Listen for player chat messages (server-side via Player.Chatted)
			listenConnection = player.Chatted:Connect(function(message: string)
				sendMessage(message, player.Name)
			end)
		else
			isConversing  = false
			currentPlayer = nil
			setLabel("Touch to talk to\n" .. NPC_NAME, GREEN)
			if DEBUG then ownerSay("Sense failed: " .. tostring(status)) end
		end
	end)
end

-- ============================================
-- INITIALIZATION
-- ============================================

local function init()
	if SERVER_URL == "" or not SERVER_URL:match("^https?://") then
		setLabel("ERROR: ServerURL\nattribute not set", RED)
		ownerSay("ERROR: Set StringAttribute 'ServerURL' on Model (e.g., http://212.227.64.143:5000)")
		return
	end

	-- Parse "NPCName.AreaName" from model name
	local dotPos = model.Name:find("%.")
	if dotPos and dotPos > 1 then
		NPC_NAME     = model.Name:sub(1, dotPos - 1)
		CURRENT_AREA = model.Name:sub(dotPos + 1)
		ownerSay("NPC: " .. NPC_NAME .. " | Area: " .. CURRENT_AREA)
		ownerSay("Server: " .. SERVER_URL)
	else
		ownerSay("ERROR: Model name must be 'NPCName.AreaName'")
		setLabel("ERROR: Invalid\nmodel name", RED)
		return
	end

	setLabel("Verifying\n" .. NPC_NAME .. "...", YELLOW)

	-- Check server health, then verify NPC exists
	task.spawn(function()
		local ok, body, status = httpGet("/health")
		if not ok or status ~= 200 then
			setLabel("Server offline\n" .. NPC_NAME, RED)
			ownerSay("ERROR: Server not reachable (status " .. tostring(status) .. ")")
			return
		end

		local version = extractJSON(body, "version")
		ownerSay("Server online" .. (version ~= "" and (" v" .. version) or ""))

		local verifyData = string.format(
			'{"npc_name":"%s","area":"%s"}',
			escapeJSON(NPC_NAME), escapeJSON(CURRENT_AREA)
		)
		local vok, vbody, vstatus = httpPost("/api/npc/verify", verifyData)
		if vok and vstatus == 200 then
			local found = extractJSON(vbody, "found")
			if found == "true" then
				local caps = ""
				if extractJSON(vbody, "has_teleport") == "true" then caps = caps .. "TP|" end
				if extractJSON(vbody, "has_llsettext") == "true" then caps = caps .. "TXT|" end
				if extractJSON(vbody, "has_notecard") == "true" then caps = caps .. "NC"  end
				setLabel("Touch to talk to\n" .. NPC_NAME .. "\n[" .. caps .. "]", GREEN)
				ownerSay("NPC verified! Click to talk.")
			else
				setLabel("NPC not found\n" .. NPC_NAME, RED)
				ownerSay("ERROR: NPC '" .. NPC_NAME .. "' not found in database!")
			end
		else
			setLabel("Verify failed\n" .. NPC_NAME, RED)
			ownerSay("ERROR: Verify request failed (status " .. tostring(vstatus) .. ")")
		end
	end)
end

-- ============================================
-- CLICK DETECTION  (replaces touch_start)
-- ============================================

local clickDetector = model:FindFirstChildOfClass("ClickDetector")
if not clickDetector then
	clickDetector = Instance.new("ClickDetector")
	clickDetector.MaxActivationDistance = 10
	clickDetector.Parent = rootPart or model
end

clickDetector.MouseClick:Connect(function(player: Player)
	-- Second click by same player ends conversation
	if isConversing and currentPlayer == player then
		endConversation(true)
		return
	end
	-- Ignore click if NPC is busy with someone else
	if isConversing then return end

	startConversation(player)
end)

-- End conversation when player leaves the game
Players.PlayerRemoving:Connect(function(player: Player)
	if isConversing and currentPlayer == player then
		endConversation(false)
	end
end)

-- ============================================
-- RUN
-- ============================================

init()
