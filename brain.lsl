// BRAIN.LSL - Advanced AI-Driven NPC System with Optional Manual Control
// Merges best features from touch.lsl and boros_balanced.lsl
// Optimized for memory efficiency

// ============================================
// CONFIGURATION & VARIABLES (Memory Optimized)
// ============================================
integer DEBUG = 0;  // Set to 1 to enable debug logging, 0 to disable

string SERVER_URL;
string NPC_NAME;
string CURRENT_AREA;
string appearanceNotecard;

// NPC State
key npcKey = NULL_KEY;
integer npcSpawned = FALSE;
string currentAnim = "";
string currentEmote = "";
list availableAnims = [];
list availableEmotes = [];

// Conversation State
key toucher = NULL_KEY;
string toucherName = "";
integer isConversing = FALSE;
integer listenHandle = -1;
integer ownerListenHandle = -1;  // Always-on listen for owner commands
integer TIMEOUT = 300;  // 5 minutes
integer givingNotecard = FALSE;  // Flag to prevent reset during notecard creation
integer initTime = 0;  // Unix time when script was initialized (for debounce)

// HTTP Tracking
key reqHealth;
key reqVerify;
key reqChat;
key reqLeave;
float reqTime;

// Colors
vector RED = <1.0, 0.0, 0.0>;
vector WHITE = <1.0, 1.0, 1.0>;
vector GREEN = <0.0, 1.0, 0.0>;
vector YELLOW = <1.0, 1.0, 0.0>;
vector BLUE = <0.3, 0.7, 1.0>;

// ============================================
// INITIALIZATION
// ============================================

init()
{
    // Read server URL from description
    SERVER_URL = llStringTrim(llGetObjectDesc(), STRING_TRIM);
    if (SERVER_URL == "" || llSubStringIndex(SERVER_URL, "http") != 0)
    {
        llSetText("ERROR: URL not set\nin description", RED, 1.0);
        llOwnerSay("ERROR: Set server URL in object description (e.g., http://212.227.64.143:5000)");
        return;
    }

    // Parse object name: "NPCName.AreaName"
    string objName = llGetObjectName();
    integer dotPos = llSubStringIndex(objName, ".");

    if (dotPos >= 1)
    {
        NPC_NAME = llGetSubString(objName, 0, dotPos - 1);
        CURRENT_AREA = llGetSubString(objName, dotPos + 1, -1);
        appearanceNotecard = NPC_NAME;

        llOwnerSay("✓ NPC: " + NPC_NAME + " | Area: " + CURRENT_AREA);
        llOwnerSay("✓ Server: " + SERVER_URL);
        llOwnerSay("💡 Owner commands:");
        llOwnerSay("  /cleanup - removes all your NPCs in region");
        llOwnerSay("  /cleanup30 - removes your NPCs within 30m of this object");
    }
    else
    {
        llOwnerSay("ERROR: Object name must be 'NPCName.AreaName' format");
        llSetText("ERROR: Invalid\nobject name", RED, 1.0);
        return;
    }

    // Load animations
    loadAnimations();

    // Reset state
    toucher = NULL_KEY;
    toucherName = "";
    isConversing = FALSE;
    npcSpawned = FALSE;

    // Validate appearance notecard exists
    if (llGetInventoryType(appearanceNotecard) != INVENTORY_NOTECARD)
    {
        llOwnerSay("ERROR: Notecard '" + appearanceNotecard + "' not found in inventory!");
        llSetText("Missing notecard:\n" + appearanceNotecard, RED, 1.0);
        return;
    }
    
    llOwnerSay("✓ Notecard '" + appearanceNotecard + "' found in inventory");
    llSetText("Verifying\n" + NPC_NAME + "...", YELLOW, 1.0);

    // Check server health
    reqHealth = llHTTPRequest(SERVER_URL + "/health",
        [HTTP_METHOD, "GET", HTTP_BODY_MAXLENGTH, 4096, HTTP_VERIFY_CERT, FALSE], "");
}

loadAnimations()
{
    availableAnims = [];
    availableEmotes = [];

    integer idx = 0;
    while (idx < llGetInventoryNumber(INVENTORY_ANIMATION))
    {
        string animName = llGetInventoryName(INVENTORY_ANIMATION, idx);
        if (llSubStringIndex(animName, "express_") == 0)
            availableEmotes += [animName];
        else
            availableAnims += [animName];
        idx++;
    }

    llOwnerSay("Loaded " + (string)llGetListLength(availableAnims) + " anims, " +
               (string)llGetListLength(availableEmotes) + " emotes");
}

// ============================================
// NPC MANAGEMENT
// ============================================

cleanupGhostNPCs()
{
    // Scan for any existing NPCs that might be left from previous script instances
    list avatars = osGetAvatarList();
    integer i;
    integer cleaned = 0;

    for (i = 0; i < llGetListLength(avatars); i += 3)
    {
        key avatarKey = llList2Key(avatars, i);
        string avatarName = llList2String(avatars, i + 1);

        // Check if it's an NPC owned by us
        key owner = osNpcGetOwner(avatarKey);
        if (owner == llGetOwner())
        {
            llOwnerSay("Removing ghost NPC: " + avatarName);
            osNpcRemove(avatarKey);
            cleaned++;
        }
    }

    if (cleaned > 0)
        llOwnerSay("Cleaned up " + (string)cleaned + " ghost NPC(s)");
    else
        llOwnerSay("No ghost NPCs found.");
}

cleanupAllOrphanNPCs(key requester)
{
    // Only allow owner to trigger this
    if (requester != llGetOwner())
    {
        llSay(0, "Only the owner can cleanup NPCs.");
        return;
    }

    llOwnerSay("=== ORPHAN NPC CLEANUP STARTED (ALL REGION) ===");
    list avatars = osGetAvatarList();
    integer i;
    integer found = 0;
    integer removed = 0;

    for (i = 0; i < llGetListLength(avatars); i += 3)
    {
        key avatarKey = llList2Key(avatars, i);
        string avatarName = llList2String(avatars, i + 1);

        // Check if it's an NPC owned by us
        key owner = osNpcGetOwner(avatarKey);
        if (owner == llGetOwner())
        {
            found++;
            llOwnerSay("Found NPC: " + avatarName + " (" + (string)avatarKey + ")");
            osNpcRemove(avatarKey);
            removed++;
            llOwnerSay("  ✓ Removed");
            llSleep(0.1);  // Small delay to prevent overwhelming the system
        }
    }

    // Reset our own NPC state if it was removed
    if (npcSpawned)
    {
        npcKey = NULL_KEY;
        npcSpawned = FALSE;
        llSetText("Touch to talk to\n" + NPC_NAME, YELLOW, 1.0);
    }

    // Report results
    llOwnerSay("=== CLEANUP COMPLETE ===");
    llOwnerSay("Total NPCs found and removed: " + (string)removed);
    llSay(0, "Cleanup complete: " + (string)removed + " NPC(s) removed.");
}

cleanupNearbyOrphanNPCs(key requester, float maxDistance)
{
    // Only allow owner to trigger this
    if (requester != llGetOwner())
    {
        llSay(0, "Only the owner can cleanup NPCs.");
        return;
    }

    vector myPos = llGetPos();
    llOwnerSay("=== NEARBY NPC CLEANUP STARTED (within " + (string)((integer)maxDistance) + "m) ===");
    llOwnerSay("Object position: " + (string)myPos);

    list avatars = osGetAvatarList();
    llOwnerSay("Total avatars in region: " + (string)(llGetListLength(avatars) / 3));

    integer i;
    integer found = 0;
    integer removed = 0;
    integer skipped = 0;
    integer notOwned = 0;

    for (i = 0; i < llGetListLength(avatars); i += 3)
    {
        key avatarKey = llList2Key(avatars, i);
        string avatarName = llList2String(avatars, i + 1);
        vector avatarPos = llList2Vector(avatars, i + 2);

        // Check if it's an NPC
        key owner = osNpcGetOwner(avatarKey);

        if (owner != NULL_KEY)
        {
            // It's an NPC
            float distance = llVecDist(myPos, avatarPos);

            if (owner == llGetOwner())
            {
                // Our NPC
                if (distance <= maxDistance)
                {
                    found++;
                    llOwnerSay("Found NPC: " + avatarName + " (" + (string)distance + "m away)");
                    osNpcRemove(avatarKey);
                    removed++;
                    llOwnerSay("  ✓ Removed");
                    llSleep(0.1);  // Small delay to prevent overwhelming the system
                }
                else
                {
                    skipped++;
                    llOwnerSay("Skipped NPC (too far): " + avatarName + " (" + (string)distance + "m away)");
                }
            }
            else
            {
                // NPC owned by someone else
                notOwned++;
                llOwnerSay("Found NPC (not yours): " + avatarName + " (" + (string)distance + "m away, owner: " + (string)owner + ")");
            }
        }
    }

    // Reset our own NPC state if it was removed
    if (npcSpawned && removed > 0)
    {
        // Check if our NPC is still there
        list nearbyCheck = osGetAvatarList();
        integer stillThere = FALSE;
        integer j;
        for (j = 0; j < llGetListLength(nearbyCheck); j += 3)
        {
            if (llList2Key(nearbyCheck, j) == npcKey)
            {
                stillThere = TRUE;
                jump endcheck;
            }
        }
        @endcheck;

        if (!stillThere)
        {
            npcKey = NULL_KEY;
            npcSpawned = FALSE;
            llSetText("Touch to talk to\n" + NPC_NAME, YELLOW, 1.0);
        }
    }

    // Report results
    llOwnerSay("=== CLEANUP COMPLETE ===");
    llOwnerSay("Your NPCs within range: " + (string)found);
    llOwnerSay("NPCs removed: " + (string)removed);
    if (skipped > 0)
        llOwnerSay("Your NPCs skipped (too far): " + (string)skipped);
    if (notOwned > 0)
        llOwnerSay("Other people's NPCs found: " + (string)notOwned);
    llSay(0, "Nearby cleanup complete: " + (string)removed + " NPC(s) removed.");
}

spawnNPC()
{
    if (npcSpawned)
    {
        if (DEBUG) llOwnerSay("DEBUG: NPC already spawned according to flag, returning");
        return;
    }

    if (DEBUG)
    {
        llOwnerSay("DEBUG: === SPAWN NPC TRACE ===");
        llOwnerSay("  Object name: " + llGetObjectName());
        llOwnerSay("  NPC_NAME global var = '" + NPC_NAME + "'");
        llOwnerSay("  CURRENT_AREA global var = '" + CURRENT_AREA + "'");
        llOwnerSay("  appearanceNotecard global var = '" + appearanceNotecard + "'");
        llOwnerSay("  Notecard type = " + (string)llGetInventoryType(appearanceNotecard));
        llOwnerSay("  npcSpawned flag = " + (string)npcSpawned);
        llOwnerSay("  npcKey = " + (string)npcKey);
    }
    
    // Check if an NPC already exists nearby with our name
    list nearby = osGetAvatarList();
    integer i;
    for (i = 0; i < llGetListLength(nearby); i += 3)
    {
        key avatarKey = llList2Key(nearby, i);
        string avatarName = llList2String(nearby, i + 1);
        
        // Check if this is our NPC (name matches "Boros NPC" or just "Boros")
        if (avatarName == NPC_NAME + " NPC" || avatarName == NPC_NAME)
        {
            if (DEBUG)
            {
                llOwnerSay("  FOUND EXISTING NPC: " + avatarName + " (" + (string)avatarKey + ")");
                llOwnerSay("  Attempting to remove old NPC...");
            }
            osNpcRemove(avatarKey);
            llSleep(1.0);
            if (DEBUG) llOwnerSay("  Old NPC removed, will now spawn new one");
            jump end_loop;
        }
    }
    @end_loop;

    // Spawn NPC slightly above the object, then sit them on it
    vector spawnPos = llGetPos() + <0.0, 0.0, 2.0>;
    if (DEBUG)
    {
        llOwnerSay("  Spawn position = " + (string)spawnPos);
        llOwnerSay("  >>> Calling osNpcCreate with:");
        llOwnerSay("      name='" + NPC_NAME + "', lastName='NPC', notecard='" + appearanceNotecard + "'");
    }

    npcKey = osNpcCreate(NPC_NAME, "NPC", spawnPos, appearanceNotecard, OS_NPC_SENSE_AS_AGENT);

    if (DEBUG) llOwnerSay("  <<< osNpcCreate returned: " + (string)npcKey);

    if (npcKey != NULL_KEY)
    {
        // Sit the NPC on this object so they're properly positioned and visible
        osNpcSit(npcKey, llGetKey(), OS_NPC_SIT_NOW);
        llSleep(0.25);  // Wait for sit animation to register
        
        npcSpawned = TRUE;
        llSetText("Talking to " + NPC_NAME, GREEN, 1.0);
        if (DEBUG) llOwnerSay("✓ NPC spawned and seated on object: " + (string)npcKey);
        
        // Play an idle animation if available (overrides default sit)
        if (llGetListLength(availableAnims) > 0)
        {
            string idleAnim = llList2String(availableAnims, 0);
            playAnim(idleAnim);
            if (DEBUG) llOwnerSay("  Playing idle animation: " + idleAnim);
        }
    }
    else
    {
        llOwnerSay("✗ Failed to spawn NPC - osNpcCreate returned NULL_KEY");
        llOwnerSay("  Check: Notecard '" + appearanceNotecard + "' format (must be LLSD appearance data)");
        llOwnerSay("  Check: NPC permissions enabled on this sim");
        llSetText("✗ Spawn failed", RED, 1.0);
    }
}

destroyNPC()
{
    if (!npcSpawned) return;

    stopAllAnims();
    // Stand NPC up before removing (cleaner removal)
    osNpcStand(npcKey);
    llSleep(0.1);
    osNpcRemove(npcKey);
    npcKey = NULL_KEY;
    npcSpawned = FALSE;
    llSetText("Touch to talk to\n" + NPC_NAME, YELLOW, 1.0);
    if (DEBUG) llOwnerSay("NPC destroyed - will respawn on next touch");
}

playAnim(string animName)
{
    // Trim and validate
    animName = llStringTrim(animName, STRING_TRIM);
    if (!npcSpawned || animName == "" || llGetInventoryType(animName) != INVENTORY_ANIMATION) return;

    // Stop all previous animations (both anim and emote to avoid interference)
    if (currentAnim != "")
    {
        osNpcStopAnimation(npcKey, currentAnim);
        currentAnim = "";
    }
    if (currentEmote != "")
    {
        osNpcStopAnimation(npcKey, currentEmote);
        currentEmote = "";
    }
    
    llSleep(0.05);

    osNpcPlayAnimation(npcKey, animName);
    currentAnim = animName;
}

playEmote(string emoteName)
{
    // Trim and validate
    emoteName = llStringTrim(emoteName, STRING_TRIM);
    if (!npcSpawned || emoteName == "" || llGetInventoryType(emoteName) != INVENTORY_ANIMATION) return;

    // Stop all previous animations (both anim and emote to avoid interference)
    if (currentAnim != "")
    {
        osNpcStopAnimation(npcKey, currentAnim);
        currentAnim = "";
    }
    if (currentEmote != "")
    {
        osNpcStopAnimation(npcKey, currentEmote);
        currentEmote = "";
    }
    
    llSleep(0.05);

    osNpcPlayAnimation(npcKey, emoteName);
    currentEmote = emoteName;
}

stopAllAnims()
{
    if (currentAnim != "")
    {
        osNpcStopAnimation(npcKey, currentAnim);
        currentAnim = "";
    }
    if (currentEmote != "")
    {
        osNpcStopAnimation(npcKey, currentEmote);
        currentEmote = "";
    }
}

// ============================================
// CONVERSATION MANAGEMENT
// ============================================

startConversation(key k, string name)
{
    if (DEBUG)
    {
        llOwnerSay("DEBUG: === START CONVERSATION ===");
        llOwnerSay("  Avatar: " + name + " (" + (string)k + ")");
        llOwnerSay("  npcSpawned: " + (string)npcSpawned);
    }

    if (!npcSpawned)
    {
        if (DEBUG) llOwnerSay("  ERROR: Cannot start conversation - NPC not spawned!");
        return;
    }

    // End previous conversation if any
    if (isConversing && toucher != NULL_KEY)
        endConversation(FALSE);

    toucher = k;
    toucherName = name;
    isConversing = TRUE;

    if (listenHandle != -1)
        llListenRemove(listenHandle);
    listenHandle = llListen(0, "", toucher, "");

    llSetTimerEvent(TIMEOUT);
    llSetText("Conversing with\n" + name, GREEN, 1.0);
    llSetColor(RED, ALL_SIDES);

    // Send greeting request
    string senseData = "{\"name\":\"" + escapeJSON(name) + "\",\"npcname\":\"" + escapeJSON(NPC_NAME) +
          "\",\"area\":\"" + escapeJSON(CURRENT_AREA) + "\"}";

    if (DEBUG) llOwnerSay("  Sending /sense request...");
    reqTime = llGetTime();
    reqChat = llHTTPRequest(SERVER_URL + "/sense",
        [HTTP_METHOD, "POST", HTTP_MIMETYPE, "application/json",
         HTTP_BODY_MAXLENGTH, 8192, HTTP_VERIFY_CERT, FALSE], senseData);
    if (DEBUG) llOwnerSay("  Request ID: " + (string)reqChat);
}

endConversation(integer sayGoodbye)
{
    if (!isConversing) return;

    // Send leave notification
    string leaveData = "{\"player_name\":\"" + escapeJSON(toucherName) + "\",\"npc_name\":\"" +
          escapeJSON(NPC_NAME) + "\",\"area\":\"" + escapeJSON(CURRENT_AREA) +
          "\",\"action\":\"leaving\",\"message\":\"Avatar leaving\",\"status\":\"end\"}";

    reqLeave = llHTTPRequest(SERVER_URL + "/api/leave_npc",
        [HTTP_METHOD, "POST", HTTP_MIMETYPE, "application/json",
         HTTP_BODY_MAXLENGTH, 4096, HTTP_VERIFY_CERT, FALSE], leaveData);

    if (listenHandle != -1)
    {
        llListenRemove(listenHandle);
        listenHandle = -1;
    }

    llSetTimerEvent(0.0);
    stopAllAnims();

    if (sayGoodbye && toucher != NULL_KEY)
        llSay(0, "È stato un piacere parlare con te, " + toucherName + "!");

    toucher = NULL_KEY;
    toucherName = "";
    isConversing = FALSE;

    // Destroy NPC when conversation ends - optimizes resources
    // NPC will be re-spawned when someone touches to talk again
    if (npcSpawned)
    {
        llSleep(0.5);  // Brief pause so goodbye message is visible
        destroyNPC();
    }

    llSetColor(WHITE, ALL_SIDES);
}

sendMessage(string msg, string name)
{
    if (DEBUG)
    {
        llOwnerSay("DEBUG: === SEND MESSAGE ===");
        llOwnerSay("  From: " + name);
        llOwnerSay("  Message: " + msg);
    }

    if (!isConversing)
    {
        if (DEBUG) llOwnerSay("  ERROR: Not conversing!");
        return;
    }

    llSetColor(RED, ALL_SIDES);
    llSetTimerEvent(TIMEOUT);  // Reset timeout

    string chatData;
    // Check for local commands
    if (llGetSubString(msg, 0, 0) == "/" && msg == "/brief")
    {
        // /brief command - send to server
        chatData = "{\"message\":\"" + escapeJSON(msg) + "\",\"player_name\":\"" +
              escapeJSON(name) + "\",\"npc_name\":\"" + escapeJSON(NPC_NAME) +
              "\",\"area\":\"" + escapeJSON(CURRENT_AREA) + "\"}";
    }
    else
    {
        // Regular message
        chatData = "{\"message\":\"" + escapeJSON(msg) + "\",\"player_name\":\"" +
              escapeJSON(name) + "\",\"npc_name\":\"" + escapeJSON(NPC_NAME) +
              "\",\"area\":\"" + escapeJSON(CURRENT_AREA) + "\"}";
    }

    if (DEBUG) llOwnerSay("  Sending /api/chat request...");
    reqTime = llGetTime();
    reqChat = llHTTPRequest(SERVER_URL + "/api/chat",
        [HTTP_METHOD, "POST", HTTP_MIMETYPE, "application/json",
         HTTP_BODY_MAXLENGTH, 8192, HTTP_VERIFY_CERT, FALSE], chatData);
    if (DEBUG) llOwnerSay("  Request ID: " + (string)reqChat);
}

// ============================================
// RESPONSE PARSING (Memory Optimized)
// ============================================

handleChatResponse(string body)
{
    llSetColor(WHITE, ALL_SIDES);
    llSetTimerEvent(TIMEOUT);  // Reset timeout

    if (DEBUG)
    {
        llOwnerSay("DEBUG: === RESPONSE RECEIVED ===");
        llOwnerSay("  Body length: " + (string)llStringLength(body));
    }

    // Extract npc_response (save to local var to avoid corruption)
    string npcResponse = extractJSON(body, "npc_response");
    if (DEBUG)
    {
        llOwnerSay("  Extracted npc_response length: " + (string)llStringLength(npcResponse));
        llOwnerSay("  Raw response: " + llGetSubString(npcResponse, 0, 100));
    }

    if (npcResponse == "")
    {
        if (DEBUG) llOwnerSay("  ERROR: npc_response is empty!");
        return;
    }

    // Parse animations BEFORE cleaning
    parseAnimations(npcResponse);

    // Extract and process sl_commands
    string slCommands = extractJSON(body, "sl_commands");
    if (DEBUG) llOwnerSay("  SL commands: " + slCommands);
    if (slCommands != "")
        processSLCommands(slCommands);

    // Clean and display response
    npcResponse = cleanText(npcResponse);
    if (DEBUG)
    {
        llOwnerSay("  Cleaned response length: " + (string)llStringLength(npcResponse));
        llOwnerSay("  Cleaned text: " + llGetSubString(npcResponse, 0, 100));
    }

    if (npcResponse != "")
    {
        if (DEBUG) llOwnerSay("  npcSpawned=" + (string)npcSpawned + ", npcKey=" + (string)npcKey);
        if (npcSpawned && npcKey != NULL_KEY)
        {
            if (DEBUG) llOwnerSay("  Using osNpcSay for NPC");
            osNpcSay(npcKey, 0, npcResponse);
        }
        else
        {
            if (DEBUG) llOwnerSay("  Using llSay (NPC not spawned or invalid key)");
            llSay(0, npcResponse);
        }
    }
    else
    {
        if (DEBUG) llOwnerSay("  ERROR: Cleaned response is empty!");
    }

    // Log timing
    if (DEBUG) llOwnerSay("[⏱ " + (string)((integer)(llGetTime() - reqTime)) + "s]");
}

parseAnimations(string text)
{
    // Look for [anim=...] or [face=...]
    // AI should choose EITHER anim OR face, not both (they interfere)
    integer localPos = llSubStringIndex(text, "[anim=");
    integer isFace = FALSE;
    
    if (localPos == -1)
    {
        localPos = llSubStringIndex(text, "[face=");
        isFace = TRUE;
    }

    if (localPos != -1)
    {
        integer localPos2 = llSubStringIndex(llGetSubString(text, localPos, -1), "]");
        if (localPos2 != -1)
        {
            string localTmp = llGetSubString(text, localPos + 1, localPos + localPos2 - 1);
            
            // Extract value after "anim=" or "face="
            string value = "";
            if (isFace && llSubStringIndex(localTmp, "face=") == 0)
                value = llGetSubString(localTmp, 5, -1);
            else if (!isFace && llSubStringIndex(localTmp, "anim=") == 0)
                value = llGetSubString(localTmp, 5, -1);
            
            // Clean the value (remove any semicolons or extra data)
            integer semiPos = llSubStringIndex(value, ";");
            if (semiPos != -1)
                value = llGetSubString(value, 0, semiPos - 1);
            
            value = llStringTrim(value, STRING_TRIM);
            
            // Play the animation or emote if value is not empty
            if (value != "")
            {
                if (isFace)
                    playEmote(value);
                else
                    playAnim(value);
            }
        }
    }
}

string cleanText(string text)
{
    // Remove animation tags
    integer localPos = llSubStringIndex(text, "[anim=");
    if (localPos == -1) localPos = llSubStringIndex(text, "[face=");
    
    while (localPos != -1)
    {
        integer localPos2 = llSubStringIndex(llGetSubString(text, localPos, -1), "]");
        if (localPos2 == -1) 
        {
            localPos = -1;  // Exit loop if malformed tag
        }
        else
        {
            // Fix: handle case when tag is at position 0
            if (localPos == 0)
                text = llGetSubString(text, localPos + localPos2 + 1, -1);
            else
                text = llGetSubString(text, 0, localPos - 1) + llGetSubString(text, localPos + localPos2 + 1, -1);
            localPos = llSubStringIndex(text, "[anim=");
            if (localPos == -1) localPos = llSubStringIndex(text, "[face=");
        }
    }

    // Remove Unicode escapes
    while ((localPos = llSubStringIndex(text, "\\u")) != -1)
    {
        if (localPos + 5 < llStringLength(text))
            text = llGetSubString(text, 0, localPos - 1) + llGetSubString(text, localPos + 6, -1);
        else
            text = llGetSubString(text, 0, localPos - 1);
    }

    // Remove escapes and markdown
    text = llDumpList2String(llParseString2List(text, ["\\n"], []), " ");
    text = llDumpList2String(llParseString2List(text, ["\\r"], []), "");
    text = llDumpList2String(llParseString2List(text, ["\\t"], []), " ");
    text = llDumpList2String(llParseString2List(text, ["**"], []), "");
    text = llDumpList2String(llParseString2List(text, ["*"], []), "");

    // Trim
    text = llStringTrim(text, STRING_TRIM);

    // Limit length
    if (llStringLength(text) > 2000)
        text = llGetSubString(text, 0, 1996) + "...";

    return text;
}

processSLCommands(string cmds)
{
    // Remove outer brackets
    if (llGetSubString(cmds, 0, 0) == "[")
        cmds = llGetSubString(cmds, 1, -2);

    // Check for notecard (extract first to avoid semicolon issues)
    integer localPos = llSubStringIndex(cmds, "notecard=");
    if (localPos != -1)
    {
        string notecardData = llGetSubString(cmds, localPos + 9, -1);
        giveNotecard(notecardData);
        cmds = llGetSubString(cmds, 0, localPos - 1);
    }

    // Parse other commands
    list localParts = llParseString2List(cmds, [";"], []);
    integer localI;
    integer animFound = FALSE;  // Track if we found anim to skip face
    
    for (localI = 0; localI < llGetListLength(localParts); localI++)
    {
        string cmd = llStringTrim(llList2String(localParts, localI), STRING_TRIM);
        if (cmd == "") jump continue;

        if (llSubStringIndex(cmd, "llSetText=") == 0)
        {
            string textValue = llGetSubString(cmd, 10, -1);
            textValue = llDumpList2String(llParseString2List(textValue, ["~"], []), "\n");
            llSetText(textValue, WHITE, 1.0);
        }
        // Prioritize anim over face (AI should choose one, but if both present, use anim)
        else if (llSubStringIndex(cmd, "anim=") == 0)
        {
            string animValue = llStringTrim(llGetSubString(cmd, 5, -1), STRING_TRIM);
            if (animValue != "")
            {
                playAnim(animValue);
                animFound = TRUE;
            }
        }
        else if (llSubStringIndex(cmd, "face=") == 0 && !animFound)
        {
            string faceValue = llStringTrim(llGetSubString(cmd, 5, -1), STRING_TRIM);
            if (faceValue != "")
                playEmote(faceValue);
        }
        else if (llSubStringIndex(cmd, "teleport=") == 0)
            doTeleport(llGetSubString(cmd, 9, -1));

        @continue;
    }
}

doTeleport(string coords)
{
    list localParts = llParseString2List(coords, [","], []);
    if (llGetListLength(localParts) == 3)
    {
        vector pos = <(float)llList2String(localParts, 0),
                      (float)llList2String(localParts, 1),
                      (float)llList2String(localParts, 2)>;
        llTeleportAgent(toucher, "", pos, ZERO_VECTOR);
    }
}

giveNotecard(string data)
{
    integer localPos = llSubStringIndex(data, "|");
    if (localPos == -1) return;

    string name = llGetSubString(data, 0, localPos - 1);
    string content = llGetSubString(data, localPos + 1, -1);

    // Unescape
    content = llDumpList2String(llParseString2List(content, ["\\n"], []), "\n");
    content = llDumpList2String(llParseString2List(content, ["\\\""], []), "\"");
    content = llDumpList2String(llParseString2List(content, ["\\\\"], []), "\\");

    // Set flag to prevent reset during notecard creation
    givingNotecard = TRUE;
    
    list lines = llParseString2List(content, ["\n"], []);
    osMakeNotecard(name, lines);
    llGiveInventory(toucher, name);
    llRemoveInventory(name);
    
    // Use llSetTimerEvent to clear flag after inventory events process
    // This ensures CHANGED_INVENTORY events from osMakeNotecard and llRemoveInventory
    // are handled before we allow resets again
    llSetTimerEvent(0.5);  // Clear flag in 0.5 seconds
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

string escapeJSON(string s)
{
    s = llDumpList2String(llParseString2List(s, ["\\"], []), "\\\\");
    s = llDumpList2String(llParseString2List(s, ["\""], []), "\\\"");
    s = llDumpList2String(llParseString2List(s, ["\n"], []), "\\n");
    return s;
}

string extractJSON(string json, string mykey)
{
    string localTmp = "\"" + mykey + "\":\"";
    integer localPos = llSubStringIndex(json, localTmp);
    if (localPos == -1) return "";

    localPos += llStringLength(localTmp);
    integer localPos2 = localPos;

    // Find closing quote (handle escapes)
    while (localPos2 < llStringLength(json))
    {
        if (llGetSubString(json, localPos2, localPos2) == "\"")
        {
            // Count preceding backslashes
            integer bs = 0;
            integer p = localPos2 - 1;
            while (p >= localPos && llGetSubString(json, p, p) == "\\")
            {
                bs++;
                p--;
            }
            if (bs % 2 == 0)  // Even backslashes = not escaped
            {
                // Handle empty string case: when closing quote is immediately after opening quote
                if (localPos2 == localPos)
                    return "";
                return unescapeJSON(llGetSubString(json, localPos, localPos2 - 1));
            }
        }
        localPos2++;
    }
    return "";
}

string unescapeJSON(string s)
{
    s = llDumpList2String(llParseString2List(s, ["\\\""], []), "\"");
    s = llDumpList2String(llParseString2List(s, ["\\\\"], []), "\\");
    s = llDumpList2String(llParseString2List(s, ["\\n"], []), "\n");
    s = llDumpList2String(llParseString2List(s, ["\\/"], []), "/");
    return s;
}

// ============================================
// MAIN STATE
// ============================================

default
{
    state_entry()
    {
        // Record init time for debounce (prevent double init from on_rez + CHANGED_INVENTORY)
        initTime = llGetUnixTime();
        
        // Set sit target so NPC sits slightly above the cube (not clipping into it)
        llSitTarget(<0.0, 0.0, 0.35>, ZERO_ROTATION);
        
        // Clean up any ghost NPCs from previous script instances
        cleanupGhostNPCs();

        // Set up always-on listener for owner commands
        if (ownerListenHandle != -1)
            llListenRemove(ownerListenHandle);
        ownerListenHandle = llListen(0, "", llGetOwner(), "");

        init();
    }

    touch_start(integer n)
    {
        key k = llDetectedKey(0);
        string name = llDetectedName(0);

        // If already conversing with this player, end conversation and destroy NPC
        if (isConversing && toucher == k)
        {
            endConversation(TRUE);
            return;
        }
        
        // If conversing with someone else, ignore
        if (isConversing && toucher != k)
        {
            llInstantMessage(k, NPC_NAME + " sta parlando con " + toucherName + ". Riprova tra poco.");
            return;
        }

        // Spawn NPC and start conversation in one step
        // This optimizes NPC lifecycle - only rezzed while talking
        if (!npcSpawned)
        {
            llSetText("Spawning " + NPC_NAME + "...", YELLOW, 1.0);
            spawnNPC();
            
            // Wait a moment for NPC to be ready
            if (npcSpawned)
            {
                llSleep(0.5);
                startConversation(k, name);
            }
        }
        else
        {
            // NPC already spawned (shouldn't happen in new flow, but handle gracefully)
            startConversation(k, name);
        }
    }

    listen(integer chan, string name, key id, string msg)
    {
        // Owner commands (work anytime)
        if (chan == 0 && id == llGetOwner())
        {
            if (msg == "/cleanup" || msg == "/cleanupnpcs")
            {
                cleanupAllOrphanNPCs(id);
                return;
            }
            else if (msg == "/cleanup30" || msg == "/cleanupnearby")
            {
                cleanupNearbyOrphanNPCs(id, 30.0);
                return;
            }
        }

        // Conversation listen only
        if (chan == 0 && isConversing && id == toucher)
        {
            sendMessage(msg, toucherName);
        }
    }

    timer()
    {
        // If timer fired to clear notecard flag, clear it and restart conversation timeout
        if (givingNotecard)
        {
            givingNotecard = FALSE;
            // Restart the conversation timeout if still conversing
            if (isConversing)
                llSetTimerEvent(TIMEOUT);
            else
                llSetTimerEvent(0);
            return;
        }
        
        // Otherwise, handle conversation timeout - end conversation and destroy NPC
        if (isConversing)
        {
            llOwnerSay("Timeout: ending conversation with " + toucherName);
            endConversation(TRUE);  // This now also destroys the NPC
        }
    }

    http_response(key id, integer status, list meta, string body)
    {
        if (id == reqHealth && status == 200)
        {
            string version = extractJSON(body, "version");
            llSetText((version != "" ? "Eldoria v" + version : "Connected") + "\n" +
                     NPC_NAME + "\nVerifying...", YELLOW, 1.0);
            llOwnerSay("✓ Server online" + (version != "" ? " v" + version : ""));

            // Verify NPC exists
            string verifyData = "{\"npc_name\":\"" + escapeJSON(NPC_NAME) + "\",\"area\":\"" +
                  escapeJSON(CURRENT_AREA) + "\"}";
            reqVerify = llHTTPRequest(SERVER_URL + "/api/npc/verify",
                [HTTP_METHOD, "POST", HTTP_MIMETYPE, "application/json",
                 HTTP_BODY_MAXLENGTH, 4096, HTTP_VERIFY_CERT, FALSE], verifyData);
        }
        else if (id == reqVerify && status == 200)
        {
            string found = extractJSON(body, "found");
            if (found == "true")
            {
                string capabilities = "";
                if (extractJSON(body, "has_teleport") == "true") capabilities += "TP|";
                if (extractJSON(body, "has_llsettext") == "true") capabilities += "TXT|";
                if (extractJSON(body, "has_notecard") == "true") capabilities += "NC";

                llSetText("Touch to talk to\n" + NPC_NAME + "\n[" + capabilities + "]", GREEN, 1.0);
                llOwnerSay("✓ NPC verified! Touch to talk (NPC spawns on demand).");
            }
            else
            {
                llSetText("✗ NPC not found\n" + NPC_NAME, RED, 1.0);
                llOwnerSay("✗ NPC not found in database!");
            }
        }
        else if (id == reqChat && status == 200)
        {
            if (DEBUG) llOwnerSay("DEBUG: Received HTTP 200 for reqChat");
            handleChatResponse(body);
        }
        else if (id == reqChat && status != 200)
        {
            llSetColor(WHITE, ALL_SIDES);
            if (DEBUG)
            {
                llOwnerSay("DEBUG: HTTP Error for reqChat: " + (string)status);
                llOwnerSay("Response body: " + llGetSubString(body, 0, 200));
            }
            llSay(0, "Scusa, non posso risponderti ora.");
        }
        else if (id != reqHealth && id != reqVerify && id != reqChat && id != reqLeave)
        {
            if (DEBUG) llOwnerSay("DEBUG: Received unexpected HTTP response, id=" + (string)id + ", status=" + (string)status);
        }
    }

    on_rez(integer param)
    {
        llResetScript();
    }

    changed(integer change)
    {
        if (change & CHANGED_INVENTORY)
        {
            // Don't reset if we're in the middle of giving a notecard
            // Also debounce: don't reset if script just initialized (within 2 seconds)
            // This prevents double init from on_rez + CHANGED_INVENTORY firing together
            if (!givingNotecard && (llGetUnixTime() - initTime) > 2)
                llResetScript();
        }

        if (change & CHANGED_REGION && npcSpawned)
        {
            llOwnerSay("Region changed - NPC lost");
            npcKey = NULL_KEY;
            npcSpawned = FALSE;
            llResetScript();
        }
    }
}
