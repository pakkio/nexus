// Simplified Touch-Activated NPC Dialogue System
// Uses /sense endpoint for simple LSL-friendly responses
// Activated by touch - only listens to the toucher during conversation
// Maintains dialogue state with the toucher until they leave range or touch again
// Resets automatically after 1 minute of inactivity
// NAMING CONVENTION: Object name must be "NPCName.AreaName" (e.g., "Syra.Forest")
// SERVER URL: Set in object description (e.g., "http://212.227.64.143:5000")

// Configuration
string SERVER_URL = "";                       // Will be read from object description
string NPC_NAME;                              // Name of this NPC (parsed from object name)
string CURRENT_AREA;                          // Area name (parsed from object name)

// State variables
key current_toucher = NULL_KEY;       // Key of the avatar currently in conversation
string current_toucher_name = "";     // Name of the current toucher
integer listen_handle = -1;           // Handle for the listen event
integer IS_CONVERSING = FALSE;        // Flag to track if in active conversation
integer TIMEOUT_SECONDS = 60;         // 1 minute in seconds (60 seconds)

// HTTP request tracking
key chat_request_id;
key leave_request_id;
key health_request_id;
key npc_verify_request_id;

// Teleport dialog tracking
integer teleport_dialog_listen;
vector pending_teleport_pos;
key pending_teleport_user;

default
{
    state_entry()
    {
        // Read server URL from object description
        SERVER_URL = llStringTrim(llGetObjectDesc(), STRING_TRIM);

        // Validate server URL
        if (SERVER_URL == "" || llSubStringIndex(SERVER_URL, "http") != 0)
        {
            llOwnerSay("ERRORE CRITICO: URL del server non configurato correttamente!");
            llOwnerSay("Imposta l'URL nella descrizione dell'oggetto (es: http://212.227.64.143:5000)");
            llOwnerSay("Descrizione attuale: '" + SERVER_URL + "'");
            llSetText("ERRORE: URL non configurato\n(Vedi console)", <1.0, 0.0, 0.0>, 1.0);
            return;
        }

        // Parse object name to extract NPC name and area
        string object_name = llGetObjectName();
        list name_parts = llParseString2List(object_name, ["."], []);

        // Enhanced naming validation
        if (llGetListLength(name_parts) >= 2)
        {
            // Extract NPC name (first part) and area (second part)
            NPC_NAME = llList2String(name_parts, 0);
            CURRENT_AREA = llList2String(name_parts, 1);


            // Validate naming format
            if (NPC_NAME == "" || CURRENT_AREA == "")
            {
                llOwnerSay("⚠️  ERRORE: Nome o Area vuoti!");
                llOwnerSay("  Formato corretto: 'NomeNPC.NomeArea'");
                llSetText("ERRORE: Nome formato non valido\n" + object_name, <1.0, 0.5, 0.0>, 1.0);
                return;
            }

            // Check for common naming issues
            // Note: Spaces in area names are now supported but may cause issues in some contexts
            // if (llSubStringIndex(NPC_NAME, " ") != -1 || llSubStringIndex(CURRENT_AREA, " ") != -1)
            // {
            //     llOwnerSay("⚠️  ATTENZIONE: Spazi nel nome potrebbero causare problemi");
            //     llOwnerSay("  Consiglio: Usa 'Lyra.SanctumOfWhispers' invece di 'Lyra.Sanctum Of Whispers'");
            // }
        }
        else
        {
            // Enhanced error for incorrect naming
            llOwnerSay("❌ ERRORE CRITICO: Nome oggetto non nel formato corretto!");
            llOwnerSay("  Nome attuale: '" + object_name + "'");
            llOwnerSay("  Formato richiesto: 'NomeNPC.NomeArea'");
            llOwnerSay("  Esempi validi:");
            llOwnerSay("    • 'Lyra.SanctumOfWhispers'");
            llOwnerSay("    • 'Jorin.Tavern'");
            llOwnerSay("    • 'Syra.AncientRuins'");

            // Use fallback but show clear error
            NPC_NAME = object_name;
            CURRENT_AREA = "Unknown";
            llSetText("ERRORE: Nome non valido\n" + object_name + "\nVedi console", <1.0, 0.0, 0.0>, 1.0);
            return;
        }

        // Initialize conversation state
        current_toucher = NULL_KEY;
        current_toucher_name = "";
        IS_CONVERSING = FALSE;

        // Initialize teleport dialog state
        teleport_dialog_listen = -1;
        pending_teleport_pos = <0,0,0>;
        pending_teleport_user = NULL_KEY;

        // Check server health and version immediately
        check_server_health();
    }

    touch_start(integer total_number)
    {
        // Check if server URL is configured
        if (SERVER_URL == "" || llSubStringIndex(SERVER_URL, "http") != 0)
        {
            llSay(0, "Questo NPC non è configurato correttamente. Contatta un amministratore.");
            return;
        }

        key toucher = llDetectedKey(0);
        string toucher_name = llDetectedName(0);

        // Check if this is the same person who is already in conversation
        if (IS_CONVERSING && current_toucher == toucher)
        {
            // End the current conversation (touch again acts as reset)
            end_conversation();
        }
        else
        {
            // If someone else was in conversation, end that conversation
            if (IS_CONVERSING)
            {
                if (listen_handle != -1)
                {
                    llListenRemove(listen_handle);
                }
                // Stop any existing timer
                llSetTimerEvent(0.0);
            }

            // Start new conversation
            current_toucher = toucher;
            current_toucher_name = toucher_name;
            IS_CONVERSING = TRUE;

            // Remove any existing listen handle and set up new one for this toucher
            if (listen_handle != -1)
            {
                llListenRemove(listen_handle);
            }
            listen_handle = llListen(0, "", current_toucher, "");  // Listen only to current toucher

            // Set up timeout for 1 minute (60 seconds) of inactivity
            llSetTimerEvent(TIMEOUT_SECONDS);

            // Call /sense endpoint for initial greeting
            call_sense_endpoint(toucher, toucher_name); // UUID, display name

            // Update display
            llSetText("Sto parlando con " + toucher_name + "\n(Conversing)", <0.0, 1.0, 0.0>, 1.0);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        // Handle teleport dialog responses (channel 1000)
        if (channel == 1000 && id == pending_teleport_user)
        {
            // Remove the dialog listener
            if (teleport_dialog_listen != -1)
            {
                llListenRemove(teleport_dialog_listen);
                teleport_dialog_listen = -1;
            }

            if (message == "Yes")
            {
                // Execute teleport using osTeleportAgent (like the working teleport script)
                llRegionSayTo(id, 0, "Teleporting you now...");

                // Use osTeleportAgent for direct teleportation within the sim
                osTeleportAgent(id, llGetRegionName(), pending_teleport_pos, <0,0,0>);
            }
            else
            {
                // User declined
                llRegionSayTo(id, 0, "Teleport cancelled.");
            }

            // Clear pending teleport data
            pending_teleport_pos = <0,0,0>;
            pending_teleport_user = NULL_KEY;

            // Restore conversation timeout
            if (IS_CONVERSING)
            {
                llSetTimerEvent(TIMEOUT_SECONDS);
            }
        }
        // Handle conversation messages (channel 0)
        else if (channel == 0 && IS_CONVERSING && id == current_toucher)
        {
            // Reset the timeout since there was activity (message received)
            llSetTimerEvent(TIMEOUT_SECONDS);

            // Call the chat API to get NPC response
            call_message_endpoint(message, id, name); // UUID, display name
        }
    }

    timer()
    {
        // Check if this is a dialog timeout (30 seconds)
        if (teleport_dialog_listen != -1)
        {
            llListenRemove(teleport_dialog_listen);
            teleport_dialog_listen = -1;

            if (pending_teleport_user != NULL_KEY)
            {
                llRegionSayTo(pending_teleport_user, 0, "Teleport offer expired.");
            }

            // Clear pending teleport data
            pending_teleport_pos = <0,0,0>;
            pending_teleport_user = NULL_KEY;

            // Restore conversation timeout if still conversing
            if (IS_CONVERSING)
            {
                llSetTimerEvent(TIMEOUT_SECONDS);
            }
            else
            {
                llSetTimerEvent(0.0);
            }
        }
        // This is a conversation timeout (1 minute of inactivity)
        else if (IS_CONVERSING)
        {
            end_conversation();
            llSay(0, "Il tempo per la conversazione è finito. Toccami di nuovo per continuare a parlare.");
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle health check responses
        if (request_id == health_request_id)
        {
            if (status == 200)
            {
                handle_health_response(body);
            }
            else
            {
                llOwnerSay("❌ Server non raggiungibile!");
                llOwnerSay("   Status: " + (string)status);
                llOwnerSay("   Errore: " + body);
                llSetText("❌ SERVER OFFLINE\n" + NPC_NAME + "\nStatus: " + (string)status, <1.0, 0.0, 0.0>, 1.0);
            }
        }
        // Handle NPC verification responses
        else if (request_id == npc_verify_request_id)
        {
            if (status == 200)
            {
                handle_npc_verification_response(body);
            }
            else
            {
                llSetText("❌ NPC NOT FOUND\n" + NPC_NAME + " in " + CURRENT_AREA + "\nCheck naming!", <1.0, 0.0, 0.0>, 1.0);
            }
        }
        // Handle chat responses
        else if (request_id == chat_request_id && IS_CONVERSING)
        {
            if (status == 200)
            {
                // Parse and respond with NPC response
                handle_chat_response(body);

                // Reset the timeout since there was activity (response received)
                llSetTimerEvent(TIMEOUT_SECONDS);
            }
            else
            {
                llOwnerSay("HTTP Error " + (string)status + ": " + body);
                llSay(0, "Scusa, al momento non posso risponderti.");

                // Still reset the timeout if there was an error response (activity occurred)
                llSetTimerEvent(TIMEOUT_SECONDS);
            }
        }
        // Handle leave responses
        else if (request_id == leave_request_id)
        {
            if (status == 200)
            {
                llOwnerSay("Leave request successful. Conversation data saved.");
            }
            else
            {
                llOwnerSay("Leave request failed with status: " + (string)status + ", body: " + body);
            }
        }
    }

    // Handle changes to object description (allows hot-reload of server URL)
    changed(integer change)
    {
        if (change & CHANGED_INVENTORY || change & CHANGED_OWNER)
        {
            llResetScript();
        }
    }
}

// Function to check server health and version
check_server_health()
{
    list http_options = [
        HTTP_METHOD, "GET",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    health_request_id = llHTTPRequest(SERVER_URL + "/health", http_options, "");
}

// Handle health check response
handle_health_response(string response_body)
{
    // Extract version from JSON
    string version = extract_json_value(response_body, "version");
    // Set display text based on version - will be updated after NPC verification
    if (version != "")
    {
        llSetText("Eldoria v" + version + " - " + NPC_NAME + "\nVerifying NPC...", <1.0, 1.0, 0.0>, 1.0);
    }
    else
    {
        llSetText(NPC_NAME + "\nVerifying NPC...", <1.0, 1.0, 0.5>, 1.0);
    }

    // Now verify NPC exists in database
    verify_npc_exists();
}


// Function to call the sense endpoint for initial greeting
call_sense_endpoint(key avatar_id, string avatar_name)
{
    string json_data = "{"
        + "\"name\":\"" + (string)avatar_id + "\"," // Use UUID for memory
        + "\"display_name\":\"" + avatar_name + "\","
        + "\"npcname\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    chat_request_id = llHTTPRequest(SERVER_URL + "/sense", http_options, json_data);
}

// Function to call the chat endpoint for messages
call_message_endpoint(string message, key avatar_id, string avatar_name)
{
    string json_data = "{"
        + "\"message\":\"" + escape_json_string(message) + "\"," 
        + "\"player_name\":\"" + (string)avatar_id + "\"," // Use UUID for memory
        + "\"display_name\":\"" + avatar_name + "\","
        + "\"npc_name\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    chat_request_id = llHTTPRequest(SERVER_URL + "/api/chat", http_options, json_data);
}

// Function to call the leave endpoint (signal that avatar is leaving conversation)
call_leave_endpoint(key avatar_id, string avatar_name)
{
    string json_data = "{"
        + "\"player_name\":\"" + (string)avatar_id + "\"," // Use UUID for memory
        + "\"display_name\":\"" + avatar_name + "\","
        + "\"npc_name\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\","
        + "\"action\":\"leaving\","
        + "\"message\":\"Avatar is leaving the conversation\","
        + "\"status\":\"end\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    leave_request_id = llHTTPRequest(SERVER_URL + "/api/leave_npc", http_options, json_data);
}

// Handle the response from the chat endpoint
handle_chat_response(string response_body)
{
    // Extract NPC response from JSON
    string npc_response = extract_json_value(response_body, "npc_response");
    string sl_commands = extract_json_value(response_body, "sl_commands");

    if (npc_response != "")
    {
        // Clean the response text
        string clean_response = clean_response_text(npc_response);

        // Speak to the current toucher
        //llRegionSayTo(current_toucher, 0, clean_response);

        // Also say in public for others to hear
        llSay(0, clean_response);
    }
    else
    {
        //llRegionSayTo(current_toucher, 0, "Non capisco bene la tua domanda. Puoi ripetere?");
    }

    // Process SL commands if present
    if (sl_commands != "")
    {
        process_sl_commands(sl_commands);
    }
}

// Process Second Life commands from API response
// Format: [lookup=object;llSetText=message;emote=gesture;anim=action;teleport=x,y,z]
process_sl_commands(string sl_commands)
{
    // Extract individual commands from the string
    string lookup = extract_sl_command(sl_commands, "lookup");
    string llsettext = extract_sl_command(sl_commands, "llSetText");
    string emote = extract_sl_command(sl_commands, "emote");
    string anim = extract_sl_command(sl_commands, "anim");
    string teleport = extract_sl_command(sl_commands, "teleport");

    // Execute llSetText command - append to conversation status
    if (llsettext != "" && IS_CONVERSING)
    {
        // Backend truncates to 80 chars max, split into lines of 20 chars each
        string line1 = "";
        string line2 = "";
        string line3 = "";
        string line4 = "";

        integer len = llStringLength(llsettext);

        if (len > 60)
        {
            line1 = llGetSubString(llsettext, 0, 19);
            line2 = llGetSubString(llsettext, 20, 39);
            line3 = llGetSubString(llsettext, 40, 59);
            line4 = llGetSubString(llsettext, 60, -1);
        }
        else if (len > 40)
        {
            line1 = llGetSubString(llsettext, 0, 19);
            line2 = llGetSubString(llsettext, 20, 39);
            line3 = llGetSubString(llsettext, 40, -1);
        }
        else if (len > 20)
        {
            line1 = llGetSubString(llsettext, 0, 19);
            line2 = llGetSubString(llsettext, 20, -1);
        }
        else
        {
            line1 = llsettext;
        }

        // Append to current conversation status
        string status_text = "Sto parlando con " + current_toucher_name;
        if (line1 != "") status_text += "\n" + line1;
        if (line2 != "") status_text += "\n" + line2;
        if (line3 != "") status_text += "\n" + line3;
        if (line4 != "") status_text += "\n" + line4;

        llSetText(status_text, <0.0, 1.0, 0.0>, 1.0);
    }

    // Handle teleport command with permission dialog
    if (teleport != "" && IS_CONVERSING && current_toucher != NULL_KEY)
    {
        handle_teleport_command(teleport, current_toucher);
    }

    // Log other commands (can be extended for actual implementation)
    // Emote and animation commands could be implemented here
}

// Extract individual command from SL command string
// Example: extract_sl_command("[lookup=item;llSetText=hello;emote=wave]", "lookup") returns "item"
string extract_sl_command(string sl_commands, string command)
{
    string pattern = command + "=";
    integer start_pos = llSubStringIndex(sl_commands, pattern);

    if (start_pos == -1) return "";

    start_pos += llStringLength(pattern);

    // Find the end of this command (either ; or ])
    integer end_pos = llSubStringIndex(llGetSubString(sl_commands, start_pos, -1), ";");
    if (end_pos == -1)
        end_pos = llSubStringIndex(llGetSubString(sl_commands, start_pos, -1), "]");

    if (end_pos == -1)
        return llGetSubString(sl_commands, start_pos, -1);

    return llGetSubString(sl_commands, start_pos, start_pos + end_pos - 1);
}

// Handle teleport command - ask for permission and execute if accepted
handle_teleport_command(string teleport_coords, key user)
{
    // Parse coordinates (format: "x,y,z")
    list coords = llParseString2List(teleport_coords, [","], []);
    if (llGetListLength(coords) != 3)
    {
        llRegionSayTo(user, 0, "Sorry, there was an error with the teleport coordinates.");
        return;
    }

    // Convert to vector
    float x = (float)llList2String(coords, 0);
    float y = (float)llList2String(coords, 1);
    float z = (float)llList2String(coords, 2);
    vector teleport_pos = <x, y, z>;

    // Validate coordinates are within region bounds
    if (x < 0.0 || x > 256.0 || y < 0.0 || y > 256.0 || z < 0.0 || z > 4096.0)
    {
        llRegionSayTo(user, 0, "Sorry, the teleport destination is out of bounds.");
        return;
    }

    // Store teleport info for dialog response
    pending_teleport_pos = teleport_pos;
    pending_teleport_user = user;

    // Remove existing teleport dialog listener if any
    if (teleport_dialog_listen != -1)
    {
        llListenRemove(teleport_dialog_listen);
    }

    // Set up dialog listener on channel 1000
    teleport_dialog_listen = llListen(1000, "", user, "");

    // Show permission dialog
    string message = NPC_NAME + " wants to teleport you to coordinates " + (string)teleport_pos + "\n\nDo you accept?";
    list buttons = ["Yes", "No"];
    llDialog(user, message, buttons, 1000);

    // Set timer to clean up dialog listener after 30 seconds
    llSetTimerEvent(30.0);
}

// Function to end the current conversation
end_conversation()
{
    if (IS_CONVERSING)
    {
        // Notify the backend that the avatar is leaving (save conversation)
        if (current_toucher != NULL_KEY)
        {
            call_leave_endpoint(current_toucher, current_toucher_name); // UUID, display name
        }

        // Remove the listen handle
        if (listen_handle != -1)
        {
            llListenRemove(listen_handle);
            listen_handle = -1;
        }

        // Clean up teleport dialog if active
        if (teleport_dialog_listen != -1)
        {
            llListenRemove(teleport_dialog_listen);
            teleport_dialog_listen = -1;
        }

        // Clear pending teleport data
        pending_teleport_pos = <0,0,0>;
        pending_teleport_user = NULL_KEY;

        // Stop the timeout timer
        llSetTimerEvent(0.0);

        // Notify the toucher
        if (current_toucher != NULL_KEY)
        {
            llSay(0, "È stato un piacere parlare con te, " + current_toucher_name + "! A presto.");
        }

        // Reset state
        current_toucher = NULL_KEY;
        current_toucher_name = "";
        IS_CONVERSING = FALSE;

        // Update display - restore default text
        llSetText("Tocca per parlare con " + NPC_NAME + "\n(Touch to talk)", <1.0, 1.0, 0.5>, 1.0);
    }
}

// Utility function to escape JSON string characters
string escape_json_string(string input)
{
    // Replace problematic characters for JSON
    input = llDumpList2String(llParseString2List(input, ["\""], []), "\\\"");
    input = llDumpList2String(llParseString2List(input, ["\\"], []), "\\\\");
    input = llDumpList2String(llParseString2List(input, ["\n"], []), "\\n");
    input = llDumpList2String(llParseString2List(input, ["\r"], []), "\\r");
    input = llDumpList2String(llParseString2List(input, ["\t"], []), "\\t");
    return input;
}

// Extract value from JSON string (simple implementation with escape handling)
string extract_json_value(string json, string mykey)
{
    string search_key = "\"" + mykey + "\":\"";
    integer start_pos = llSubStringIndex(json, search_key);

    if (start_pos == -1) return "";

    start_pos += llStringLength(search_key);

    // Find the closing quote, but handle escaped quotes
    integer pos = start_pos;
    integer json_len = llStringLength(json);

    while (pos < json_len)
    {
        string current_char = llGetSubString(json, pos, pos);

        if (current_char == "\"")
        {
            // Check if this quote is escaped by counting preceding backslashes
            integer backslash_count = 0;
            integer check_pos = pos - 1;

            while (check_pos >= start_pos && llGetSubString(json, check_pos, check_pos) == "\\")
            {
                backslash_count++;
                check_pos--;
            }

            // If even number of backslashes (or zero), the quote is not escaped
            if (backslash_count % 2 == 0)
            {
                // This is the closing quote
                return unescape_json_string(llGetSubString(json, start_pos, pos - 1));
            }
        }
        pos++;
    }

    return ""; // No closing quote found
}

// Unescape JSON string characters
string unescape_json_string(string input)
{
    // Handle common JSON escape sequences
    input = llDumpList2String(llParseString2List(input, ["\\\""], []), "\"");
    input = llDumpList2String(llParseString2List(input, ["\\\\"], []), "\\");
    input = llDumpList2String(llParseString2List(input, ["\\n"], []), "\n");
    input = llDumpList2String(llParseString2List(input, ["\\r"], []), "\r");
    input = llDumpList2String(llParseString2List(input, ["\\t"], []), "\t");
    input = llDumpList2String(llParseString2List(input, ["\\/"], []), "/");
    return input;
}

// Clean response text for speaking
string clean_response_text(string response)
{
    // Remove Unicode escape sequences (like \ud83d\ude0a for emojis)
    integer pos = llSubStringIndex(response, "\\u");
    while (pos != -1) {
        // Find the end of the unicode sequence (4 hex digits after \u)
        if (pos + 5 < llStringLength(response)) {
            string before = llGetSubString(response, 0, pos - 1);
            string after = llGetSubString(response, pos + 6, -1);
            response = before + after;
        } else {
            // If incomplete sequence at end, just remove it
            response = llGetSubString(response, 0, pos - 1);
        }
        pos = llSubStringIndex(response, "\\u");
    }

    // Remove other escape sequences like \n
    response = llDumpList2String(llParseString2List(response, ["\\n"], []), " ");
    response = llDumpList2String(llParseString2List(response, ["\\r"], []), "");
    response = llDumpList2String(llParseString2List(response, ["\\t"], []), " ");

    // Remove markdown formatting
    response = llDumpList2String(llParseString2List(response, ["**"], []), "");
    response = llDumpList2String(llParseString2List(response, ["*"], []), "");

    // Trim whitespace
    while (llGetSubString(response, 0, 0) == " " && llStringLength(response) > 0) {
        response = llGetSubString(response, 1, -1);
    }
    while (llGetSubString(response, -1, -1) == " " && llStringLength(response) > 0) {
        response = llGetSubString(response, 0, -2);
    }

    // Limit length for LSL say function (increased for brief mode support)
    if (llStringLength(response) > 2500) {
        response = llGetSubString(response, 0, 2496) + "...";
    }

    return response;
}

// Function to verify NPC exists in database and get capabilities
verify_npc_exists()
{
    string json_data = "{"
        + "\"npc_name\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    npc_verify_request_id = llHTTPRequest(SERVER_URL + "/api/npc/verify", http_options, json_data);
}

// Handle NPC verification response
handle_npc_verification_response(string response_body)
{
    string found = extract_json_value(response_body, "found");

    if (found == "true")
    {
        string npc_name = extract_json_value(response_body, "npc_name");
        string area = extract_json_value(response_body, "area");
        string has_teleport = extract_json_value(response_body, "has_teleport");
        string has_llsettext = extract_json_value(response_body, "has_llsettext");

        // Build capabilities string
        string capabilities = "";
        if (has_teleport == "true")
        {
            capabilities += "TP ";
        }
        if (has_llsettext == "true")
        {
            capabilities += "TEXT ";
        }

        // Update display with success and capabilities
        string display_text = "✓ " + npc_name + " [" + area + "]";
        if (capabilities != "")
        {
            display_text += "\n[" + capabilities + "]";
        }
        display_text += "\n(Touch to talk)";

        llSetText(display_text, <0.0, 1.0, 0.0>, 1.0);
    }
    else
    {
        llSetText("❌ NPC NOT FOUND\n" + NPC_NAME + " in " + CURRENT_AREA, <1.0, 0.0, 0.0>, 1.0);
    }
}
