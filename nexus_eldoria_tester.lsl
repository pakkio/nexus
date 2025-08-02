// =============================================================================
// NEXUS/ELDORIA RPG TESTING SCRIPT FOR OPENSIM/SECOND LIFE
// =============================================================================
// Based on performance testing: 2.9s arrivals, 0.88s commands, 0.012s departures
// Integrates with the optimized API endpoints for real-world testing
//
// USAGE:
// 1. Rez object in OpenSim/SL
// 2. Configure NEXUS_SERVER_URL
// 3. FIRST TOUCH - simulate arrival (greeted by NPC)
// 4. Chat in public chat with the NPC
// 5. SECOND TOUCH - simulate departure
// 6. Use /leave command to manually trigger departure
//
// Performance verified: Sub-3s responses, SL commands working
//
// NOTE: This script simulates player interactions with the Nexus/Eldoria RPG system
//       for testing purposes in Second Life/OpenSim environments.
// =============================================================================

// Configuration
string NEXUS_SERVER_URL = "http://localhost:5000";  // Change to your Nexus server
string NPC_NAME = "mara";                           // Default NPC to interact with  
string AREA_NAME = "Village";                       // Default area
float SENSOR_RANGE = 5.0;                          // Range for auto-detection
float SENSOR_REPEAT = 3.0;                         // Sensor scan frequency
integer MAX_RESPONSE_LENGTH = 0;                   // Maximum response length (0 = no limit)

// State tracking
list avatar_sessions = [];        // Active avatar sessions [avatar_key, avatar_name, session_active]
integer total_interactions = 0;  // Statistics counter
float avg_response_time = 0.0;   // Performance tracking

// Colors for visual feedback
vector COLOR_READY = <0.0, 1.0, 0.0>;      // Green = Ready
vector COLOR_PROCESSING = <1.0, 1.0, 0.0>; // Yellow = Processing  
vector COLOR_ERROR = <1.0, 0.0, 0.0>;      // Red = Error
vector COLOR_SUCCESS = <0.0, 0.0, 1.0>;    // Blue = Success

// HTTP request tracking
list pending_requests = [];      // [request_key, avatar_key, request_type, timestamp]

default
{
    state_entry()
    {
        llOwnerSay("🎮 Nexus/Eldoria RPG Tester Initialized");
        llOwnerSay("📊 Performance: Avg 2.9s arrivals, 0.88s commands, 0.012s departures");
        llOwnerSay("👆 Touch to simulate arrival/departure or walk within " + (string)SENSOR_RANGE + "m");
        
        // Visual setup
        llSetText("🏰 Eldoria RPG Tester\n✅ Ready\n👆 Touch to begin", COLOR_READY, 1.0);
        llSetColor(COLOR_READY, ALL_SIDES);
        
        // Start listening to public chat (channel 0)
        llListen(0, "", NULL_KEY, "");
        
        // Start avatar detection
        llSensorRepeat("", NULL_KEY, AGENT, SENSOR_RANGE, PI, SENSOR_REPEAT);
        
        // Reset statistics
        avatar_sessions = [];
        total_interactions = 0;
        avg_response_time = 0.0;
    }
    
    sensor(integer num_detected)
    {
        integer i;
        for (i = 0; i < num_detected; i++)
        {
            key avatar_key = llDetectedKey(i);
            string avatar_name = llDetectedName(i);
            
            // Check if avatar is new (not in sessions list)
            if (get_avatar_session_index(avatar_key) == -1)
            {
                llOwnerSay("👋 Auto-detected arrival: " + avatar_name);
                handle_avatar_arrival(avatar_key, avatar_name);
            }
        }
    }
    
    no_sensor()
    {
        // Check for avatars that left the sensor range and auto-depart them
        integer i;
        list avatars_to_depart = [];
        
        for (i = 0; i < llGetListLength(avatar_sessions); i += 3)
        {
            key avatar_key = llList2Key(avatar_sessions, i);
            string avatar_name = llList2String(avatar_sessions, i + 1);
            integer session_active = llList2Integer(avatar_sessions, i + 2);
            
            if (session_active)
            {
                // Mark for auto-departure
                avatars_to_depart += [avatar_key, avatar_name];
            }
        }
        
        // Process auto-departures
        for (i = 0; i < llGetListLength(avatars_to_depart); i += 2)
        {
            key avatar_key = llList2Key(avatars_to_depart, i);
            string avatar_name = llList2String(avatars_to_depart, i + 1);
            llOwnerSay("👋 Auto-detected departure: " + avatar_name);
            handle_avatar_departure(avatar_key, avatar_name);
        }
        
        // End any conversations if no active sessions remain
        if (llGetListLength(avatar_sessions) == 0 || llGetListLength(avatars_to_depart) > 0)
        {
            llOwnerSay("📡 No avatars in range - ending conversation");
            // Could send a final message to NPCs about being alone
            string url = NEXUS_SERVER_URL + "/sense";
            string json_data = "{\"name\":\"\",\"npcname\":\"" + NPC_NAME + "\",\"area\":\"" + AREA_NAME + "\"}";
            llHTTPRequest(url, [HTTP_METHOD, "POST", HTTP_MIMETYPE, "application/json"], json_data);
        }
    }
    
    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        string toucher_name = llDetectedName(0);
        
        integer session_index = get_avatar_session_index(toucher);
        
        if (session_index == -1)
        {
            // New session - simulate arrival
            llOwnerSay("🆕 Touch arrival: " + toucher_name);
            handle_avatar_arrival(toucher, toucher_name);
        }
        else
        {
            integer session_active = llList2Integer(avatar_sessions, session_index + 2);
            if (session_active)
            {
                // Existing active session - simulate departure
                llOwnerSay("👋 Touch departure: " + toucher_name);
                handle_avatar_departure(toucher, toucher_name);
            }
            else
            {
                // Previous session was deactivated - create new arrival
                llOwnerSay("🆕 New touch arrival: " + toucher_name);
                // Remove the old session entry first
                avatar_sessions = llDeleteSubList(avatar_sessions, session_index, session_index + 2);
                handle_avatar_arrival(toucher, toucher_name);
            }
        }
    }
    
    http_response(key request_id, integer status, list metadata, string body)
    {
        // Find the request in pending list
        integer req_index = llListFindList(pending_requests, [request_id]);
        if (req_index == -1) return; // Unknown request
        
        key avatar_key = llList2Key(pending_requests, req_index + 1);
        string request_type = llList2String(pending_requests, req_index + 2);
        float timestamp = llList2Float(pending_requests, req_index + 3);
        
        // Calculate response time
        float response_time = llGetTime() - timestamp;
        update_performance_stats(response_time);
        
        // Remove from pending list
        pending_requests = llDeleteSubList(pending_requests, req_index, req_index + 3);
        
        // Process response
        if (status == 200)
        {
            llSetColor(COLOR_SUCCESS, ALL_SIDES);
            process_api_response(avatar_key, request_type, body, response_time);
        }
        else
        {
            llSetColor(COLOR_ERROR, ALL_SIDES);
            llOwnerSay("❌ API Error " + (string)status + ": " + body);
            llOwnerSay("📊 Response time: " + (string)((integer)(response_time * 1000)) + "ms");
        }
        
        // Reset color after 2 seconds
        llSetTimerEvent(2.0);
    }
    
    timer()
    {
        llSetTimerEvent(0.0);
        llSetColor(COLOR_READY, ALL_SIDES);
        update_display_text();
    }
    
    listen(integer channel, string name, key id, string message)
    {
        // Handle chat from any avatar in range
        llOwnerSay("👂 Heard chat from " + name + ": " + message);
        
        // Check if avatar has an active session
        integer session_index = get_avatar_session_index(id);
        if (session_index != -1)
        {
            integer session_active = llList2Integer(avatar_sessions, session_index + 2);
            if (session_active)
            {
                llOwnerSay("💬 Processing chat from active session: " + name);
                handle_chat_message(id, name, message);
            }
            else
            {
                llOwnerSay("⚠️ Chat from inactive session: " + name + " (ignoring)");
            }
        }
        else
        {
            // Avatar not in session - auto-add them if in range
            list avatars = llGetAgentList(AGENT_LIST_REGION, []);
            if (llListFindList(avatars, [id]) != -1)
            {
                llOwnerSay("🆕 Auto-adding " + name + " to session for chat");
                handle_avatar_arrival(id, name);
                // Chat will be processed in next listen event
            }
            else
            {
                llOwnerSay("⚠️ Chat from avatar not in range: " + name);
            }
        }
    }
}

// =============================================================================
// AVATAR SESSION MANAGEMENT
// =============================================================================

integer get_avatar_session_index(key avatar_key)
{
    integer i;
    for (i = 0; i < llGetListLength(avatar_sessions); i += 3)
    {
        if (llList2Key(avatar_sessions, i) == avatar_key)
            return i;
    }
    return -1;
}

handle_avatar_arrival(key avatar_key, string avatar_name)
{
    llSetColor(COLOR_PROCESSING, ALL_SIDES);
    llSetText("🎮 Processing Arrival\n" + avatar_name, COLOR_PROCESSING, 1.0);
    
    // Add to sessions list
    avatar_sessions += [avatar_key, avatar_name, TRUE];
    
    // Call /sense API endpoint
    string url = NEXUS_SERVER_URL + "/sense";
    string json_data = "{\"name\":\"" + avatar_name + "\",\"npcname\":\"" + NPC_NAME + "\",\"area\":\"" + AREA_NAME + "\"}";
    
    key request_id = llHTTPRequest(url, [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ], json_data);
    
    // Track request
    pending_requests += [request_id, avatar_key, "sense", llGetTime()];
    
    llOwnerSay("📤 Sending arrival notification for " + avatar_name);
}

handle_avatar_departure(key avatar_key, string avatar_name)
{
    llSetColor(COLOR_PROCESSING, ALL_SIDES);
    llSetText("👋 Processing Departure\n" + avatar_name, COLOR_PROCESSING, 1.0);
    
    // Update session status
    integer session_index = get_avatar_session_index(avatar_key);
    if (session_index != -1)
    {
        avatar_sessions = llListReplaceList(avatar_sessions, [FALSE], session_index + 2, session_index + 2);
    }
    
    // Call /leave API endpoint
    string url = NEXUS_SERVER_URL + "/leave";
    string json_data = "{\"name\":\"" + avatar_name + "\",\"npcname\":\"" + NPC_NAME + "\",\"area\":\"" + AREA_NAME + "\"}";
    
    key request_id = llHTTPRequest(url, [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ], json_data);
    
    // Track request
    pending_requests += [request_id, avatar_key, "leave", llGetTime()];
    
    llOwnerSay("📤 Sending departure notification for " + avatar_name);
}

handle_chat_message(key avatar_key, string avatar_name, string message)
{
    // Ignore system messages and commands starting with /
    if (llGetSubString(message, 0, 0) == "/" && llStringLength(message) > 1)
    {
        // Handle as system command
        process_system_command(avatar_key, avatar_name, message);
        return;
    }
    
    llSetColor(COLOR_PROCESSING, ALL_SIDES);
    llSetText("💬 Processing Chat\n" + avatar_name, COLOR_PROCESSING, 1.0);
    
    // Call /api/chat endpoint
    string url = NEXUS_SERVER_URL + "/api/chat";
    string json_data = "{\"player_name\":\"" + avatar_name + "\",\"message\":\"" + message + "\",\"npc_name\":\"" + NPC_NAME + "\",\"area\":\"" + AREA_NAME + "\"}";
    
    key request_id = llHTTPRequest(url, [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ], json_data);
    
    // Track request
    pending_requests += [request_id, avatar_key, "chat", llGetTime()];
    
    llOwnerSay("💬 Processing message from " + avatar_name + ": " + message);
}

process_system_command(key avatar_key, string avatar_name, string command)
{
    llOwnerSay("⚙️ System command from " + avatar_name + ": " + command);
    
    // Handle special commands
    if (command == "/stats")
    {
        show_performance_stats(avatar_key);
        return;
    }
    
    // Handle manual departure command
    if (command == "/leave")
    {
        llOwnerSay("👋 Manual departure command: " + avatar_name);
        handle_avatar_departure(avatar_key, avatar_name);
        return;
    }
    
    // For unknown commands, send to API as regular chat
    llSetColor(COLOR_PROCESSING, ALL_SIDES);
    llSetText("💬 Processing Command\n" + avatar_name, COLOR_PROCESSING, 1.0);
    
    // Call /api/chat endpoint directly to avoid recursion
    string url = NEXUS_SERVER_URL + "/api/chat";
    string json_data = "{\"player_name\":\"" + avatar_name + "\",\"message\":\"" + command + "\",\"npc_name\":\"" + NPC_NAME + "\",\"area\":\"" + AREA_NAME + "\"}";
    
    key request_id = llHTTPRequest(url, [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ], json_data);
    
    // Track request
    pending_requests += [request_id, avatar_key, "chat", llGetTime()];
    
    llOwnerSay("💬 Processing unknown command: " + command);
}

// =============================================================================
// API RESPONSE PROCESSING
// =============================================================================

process_api_response(key avatar_key, string request_type, string body, float response_time)
{
    integer session_index = get_avatar_session_index(avatar_key);
    if (session_index == -1) return;
    
    string avatar_name = llList2String(avatar_sessions, session_index + 1);
    
    // Parse JSON response (simple extraction)
    string npc_response = extract_json_field(body, "npc_response");
    string sl_commands = extract_json_field(body, "sl_commands");
    string current_area = extract_json_field(body, "current_area");
    string npc_name = extract_json_field(body, "npc_name");
    
    // Log performance
    string perf_msg = "📊 " + request_type + " completed in " + (string)((integer)(response_time * 1000)) + "ms";
    llOwnerSay(perf_msg);
    
    // Display NPC response if available
    if (npc_response != "")
    {
        // Clean up response (remove excessive newlines)
        npc_response = llStringTrim(npc_response, STRING_TRIM);
        if (MAX_RESPONSE_LENGTH > 0 && llStringLength(npc_response) > MAX_RESPONSE_LENGTH)
        {
            npc_response = llGetSubString(npc_response, 0, MAX_RESPONSE_LENGTH - 3) + "...";
        }
        
        llOwnerSay("🗣️ " + npc_name + " (" + current_area + "): " + npc_response);
        
        // Send to avatar if they're still around
        if (llVecDist(llList2Vector(llGetObjectDetails(avatar_key, [OBJECT_POS]), 0), llGetPos()) <= SENSOR_RANGE * 2)
        {
            llRegionSayTo(avatar_key, 0, "🏰 " + npc_name + ": " + npc_response);
        }
    }
    
    // Process SL commands if available
    if (sl_commands != "" && sl_commands != "null")
    {
        process_sl_commands(sl_commands, avatar_name);
    }
    
    // Update statistics
    total_interactions++;
    update_display_text();
}

process_sl_commands(string sl_commands, string avatar_name)
{
    llOwnerSay("🤖 SL Commands: " + sl_commands);
    
    // Extract individual commands (simple parsing)
    string lookup = extract_sl_command(sl_commands, "lookup");
    string llsettext = extract_sl_command(sl_commands, "llSetText");
    string emote = extract_sl_command(sl_commands, "emote");
    string anim = extract_sl_command(sl_commands, "anim");
    
    // Execute SL commands
    if (lookup != "")
    {
        llOwnerSay("🔍 Lookup: " + lookup);
        // Could trigger particle effects, object rezzing, etc.
    }
    
    if (llsettext != "")
    {
        llOwnerSay("💬 Display: " + llsettext);
        // Update hover text with game information
        llSetText("🏰 " + llsettext, <1,1,1>, 1.0);
    }
    
    if (emote != "")
    {
        llOwnerSay("😊 Emote: " + emote);
        // Could trigger facial expressions, gesture animations
    }
    
    if (anim != "")
    {
        llOwnerSay("🎭 Animation: " + anim);
        // Could trigger object animations, particle effects
    }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

string extract_json_field(string json, string field)
{
    // Simple JSON field extraction (not full parser)
    string search_pattern = "\"" + field + "\":\"";
    integer start_pos = llSubStringIndex(json, search_pattern);
    if (start_pos == -1) return "";
    
    start_pos += llStringLength(search_pattern);
    integer end_pos = llSubStringIndex(llGetSubString(json, start_pos, -1), "\"");
    if (end_pos == -1) return "";
    
    return llGetSubString(json, start_pos, start_pos + end_pos - 1);
}

string extract_sl_command(string sl_commands, string command)
{
    // Extract value from [lookup=X;llSetText=Y;emote=Z;anim=W] format
    string pattern = command + "=";
    integer start_pos = llSubStringIndex(sl_commands, pattern);
    if (start_pos == -1) return "";
    
    start_pos += llStringLength(pattern);
    integer end_pos = llSubStringIndex(llGetSubString(sl_commands, start_pos, -1), ";");
    if (end_pos == -1) end_pos = llSubStringIndex(llGetSubString(sl_commands, start_pos, -1), "]");
    if (end_pos == -1) return llGetSubString(sl_commands, start_pos, -1);
    
    return llGetSubString(sl_commands, start_pos, start_pos + end_pos - 1);
}

update_performance_stats(float response_time)
{
    // Update running average
    if (total_interactions == 0)
        avg_response_time = response_time;
    else
        avg_response_time = (avg_response_time * total_interactions + response_time) / (total_interactions + 1);
}

update_display_text()
{
    string display_text = "🏰 Eldoria RPG Tester\n";
    display_text += "✅ Ready (" + (string)total_interactions + " interactions)\n";
    display_text += "⚡ Avg: " + (string)((integer)(avg_response_time * 1000)) + "ms\n";
    display_text += "👥 Active: " + (string)(llGetListLength(avatar_sessions) / 3);
    
    llSetText(display_text, COLOR_READY, 1.0);
}

show_performance_stats(key avatar_key)
{
    string stats = "📊 NEXUS/ELDORIA PERFORMANCE STATS 📊\n";
    stats += "🔹 Total Interactions: " + (string)total_interactions + "\n";
    stats += "🔹 Average Response Time: " + (string)((integer)(avg_response_time * 1000)) + "ms\n";
    stats += "🔹 Active Sessions: " + (string)(llGetListLength(avatar_sessions) / 3) + "\n";
    stats += "🔹 Server: " + NEXUS_SERVER_URL + "\n";
    stats += "🔹 NPC: " + NPC_NAME + " (" + AREA_NAME + ")\n";
    stats += "Expected: 2.9s arrivals, 0.88s commands, 0.012s departures";
    
    llRegionSayTo(avatar_key, 0, stats);
}

// =============================================================================
// END OF NEXUS/ELDORIA RPG TESTER SCRIPT
// =============================================================================