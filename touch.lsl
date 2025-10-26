// Simplified Touch-Activated NPC Dialogue System
// Uses /sense endpoint for simple LSL-friendly responses
// Activated by touch - only listens to the toucher during conversation
// Maintains dialogue state with the toucher until they leave range or touch again
// Resets automatically after 5 minutes of inactivity

// Configuration
string SERVER_URL = "";                       // Will be read from object description
string NPC_NAME;                              // Name of this NPC (will be parsed from object name)
string CURRENT_AREA;                          // Area name (will be parsed from object name)

// State variables
key current_toucher = NULL_KEY;       // Key of the avatar currently in conversation
string current_toucher_name = "";     // Name of the current toucher
integer listen_handle = -1;           // Handle for the listen event
integer IS_CONVERSING = FALSE;        // Flag to track if in active conversation
integer TIMEOUT_SECONDS = 300;        // 5 minutes in seconds (300 seconds)

// HTTP request tracking
key chat_request_id;
key leave_request_id;
key health_request_id;           // Server health check request
key npc_verify_request_id;       // NPC verification request

// Color feedback tracking
float request_start_time = 0.0;  // When request was sent
vector RED = <1.0, 0.0, 0.0>;   // Thinking color
vector WHITE = <1.0, 1.0, 1.0>; // Ready color

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
            llSetText("ERRORE:\nURL non configurato\n(Vedi console)", <1.0, 0.0, 0.0>, 1.0);
            return;
        }

        // Parse object name to extract NPC name and area (format: "NPCName.AreaName")
        string object_name = llGetObjectName();
        list name_parts = llParseString2List(object_name, ["."], []);

        if (llGetListLength(name_parts) >= 2)
        {
            // Extract NPC name (first part) and area (second part)
            NPC_NAME = llList2String(name_parts, 0);
            CURRENT_AREA = llList2String(name_parts, 1);

            // Validate naming format
            if (NPC_NAME == "" || CURRENT_AREA == "")
            {
                llOwnerSay("ERRORE: Nome o Area vuoti!");
                llOwnerSay("Formato corretto: 'NomeNPC.NomeArea' (es: Elira.Forest)");
                llSetText("ERRORE:\nNome formato non valido\n" + object_name, <1.0, 0.5, 0.0>, 1.0);
                return;
            }

            llOwnerSay("✓ NPC: " + NPC_NAME + " | Area: " + CURRENT_AREA);
            llOwnerSay("✓ Server: " + SERVER_URL);
        }
        else
        {
            // Error for incorrect naming
            llOwnerSay("ERRORE CRITICO: Nome oggetto non nel formato corretto!");
            llOwnerSay("Nome attuale: '" + object_name + "'");
            llOwnerSay("Formato richiesto: 'NomeNPC.NomeArea'");
            llOwnerSay("Esempi validi:");
            llOwnerSay("  • 'Lyra.SanctumOfWhispers'");
            llOwnerSay("  • 'Jorin.Tavern'");
            llOwnerSay("  • 'Elira.Forest'");

            // Use fallback
            NPC_NAME = object_name;
            CURRENT_AREA = "Unknown";
            llSetText("ERRORE:\nNome non valido\n" + object_name + "\nVedi console", <1.0, 0.0, 0.0>, 1.0);
            return;
        }

        // Set initial display text (verification in progress)
        llSetText("Verifying\n" + NPC_NAME + "...", <1.0, 1.0, 0.5>, 1.0);

        // Initialize conversation state
        current_toucher = NULL_KEY;
        current_toucher_name = "";
        IS_CONVERSING = FALSE;

        llOwnerSay("Touch-activated NPC '" + NPC_NAME + "' in area '" + CURRENT_AREA + "' initialized.");
        llOwnerSay("Starting verification...");

        // Check server health and verify NPC configuration
        check_server_health();
    }

    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        string toucher_name = llDetectedName(0);

        // Check if this is the same person who is already in conversation
        if (IS_CONVERSING && current_toucher == toucher)
        {
            // End the current conversation (touch again acts as reset)
            end_conversation();
            llOwnerSay("Conversation ended with " + toucher_name);
        }
        else
        {
            // If someone else was in conversation, end that conversation
            if (IS_CONVERSING)
            {
                llOwnerSay("Ending previous conversation with " + current_toucher_name);
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

            // Set up timeout for 5 minutes (300 seconds) of inactivity
            llSetTimerEvent(TIMEOUT_SECONDS);

            llOwnerSay("Starting conversation with " + toucher_name);

            // Call /sense endpoint for initial greeting
            call_sense_endpoint(toucher_name);

            // Update display
            llSetText("Sto parlando con\n" + toucher_name + "\n(Conversing)", <0.0, 1.0, 0.0>, 1.0);
        }
    }

    listen(integer channel, string name, key id, string message)
    {
        // This should only trigger for the current toucher due to the listen filter
        if (IS_CONVERSING && id == current_toucher)
        {
            llOwnerSay("Received message from toucher: " + message);

            // Reset the timeout since there was activity (message received)
            llSetTimerEvent(TIMEOUT_SECONDS);

            // Check for special commands starting with /
            if (llGetSubString(message, 0, 0) == "/" && llStringLength(message) > 1)
            {
                process_local_command(message, name);
            }
            else
            {
                // Call the chat API to get NPC response
                call_message_endpoint(message, name);
            }
        }
    }

    timer()
    {
        // This function is called when the timer times out (after 5 minutes of inactivity)
        if (IS_CONVERSING)
        {
            llOwnerSay("Timeout reached. Ending conversation with " + current_toucher_name);
            end_conversation();
            llSay(0, "Il tempo per la conversazione è finito. Toccami di nuovo per continuare a parlare.");
        }
    }

    http_response(key request_id, integer status, list metadata, string body)
    {
        // Handle health check response
        if (request_id == health_request_id)
        {
            if (status == 200)
            {
                handle_health_response(body);
            }
            else
            {
                llOwnerSay("✗ Server health check failed: " + (string)status);
                llSetText("✗ Server\nunreachable\n" + NPC_NAME, <1.0, 0.0, 0.0>, 1.0);
            }
        }
        // Handle NPC verification response
        else if (request_id == npc_verify_request_id)
        {
            if (status == 200)
            {
                handle_npc_verification_response(body);
            }
            else
            {
                llOwnerSay("✗ NPC verification failed: " + (string)status);
                llSetText("✗ NPC verification\nfailed\n" + NPC_NAME, <1.0, 0.0, 0.0>, 1.0);
            }
        }
        // Handle chat responses
        else if (request_id == chat_request_id && IS_CONVERSING)
        {
            // Calculate response time
            float response_time = llGetTime() - request_start_time;

            if (status == 200)
            {
                // Set object to WHITE - ready
                llSetColor(WHITE, ALL_SIDES);

                // Parse and respond with NPC response
                handle_chat_response(body);

                // Add timing info to chat
                integer seconds = (integer)response_time;
                llOwnerSay("[⏱ Tempo risposta: " + (string)seconds + " secondi]");

                // Reset the timeout since there was activity (response received)
                llSetTimerEvent(TIMEOUT_SECONDS);
            }
            else
            {
                llSetColor(WHITE, ALL_SIDES);
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
}

// Function to call the sense endpoint for initial greeting
call_sense_endpoint(string avatar_name)
{
    string json_data = "{"
        + "\"name\":\"" + avatar_name + "\","
        + "\"npcname\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    // Set object to RED - thinking/processing
    llSetColor(RED, ALL_SIDES);
    request_start_time = llGetTime();

    chat_request_id = llHTTPRequest(SERVER_URL + "/sense", http_options, json_data);
}

// Process local commands like /brief
process_local_command(string command, string avatar_name)
{
    llOwnerSay("Processing local command: " + command);
    
    if (command == "/brief")
    {
        // Toggle brief mode by sending special message to server
        string json_data = "{"
            + "\"message\":\"" + escape_json_string(command) + "\","
            + "\"player_name\":\"" + avatar_name + "\","
            + "\"npc_name\":\"" + NPC_NAME + "\","
            + "\"area\":\"" + CURRENT_AREA + "\""
            + "}";

        list http_options = [
            HTTP_METHOD, "POST",
            HTTP_MIMETYPE, "application/json",
            HTTP_BODY_MAXLENGTH, 16384,
            HTTP_VERIFY_CERT, FALSE
        ];

        // Set object to RED - thinking/processing
        llSetColor(RED, ALL_SIDES);
        request_start_time = llGetTime();

        chat_request_id = llHTTPRequest(SERVER_URL + "/api/chat", http_options, json_data);
        llOwnerSay("Sent /brief command to server");
    }
    else
    {
        // For unknown commands, send to server as regular message
        call_message_endpoint(command, avatar_name);
    }
}

// Function to call the chat endpoint for messages
call_message_endpoint(string message, string avatar_name)
{
    string json_data = "{"
        + "\"message\":\"" + escape_json_string(message) + "\","
        + "\"player_name\":\"" + avatar_name + "\","
        + "\"npc_name\":\"" + NPC_NAME + "\","
        + "\"area\":\"" + CURRENT_AREA + "\""
        + "}";

    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    // Set object to RED - thinking/processing
    llSetColor(RED, ALL_SIDES);
    request_start_time = llGetTime();

    chat_request_id = llHTTPRequest(SERVER_URL + "/api/chat", http_options, json_data);
}

// Function to call the leave endpoint (signal that avatar is leaving conversation)
call_leave_endpoint(string avatar_name)
{
    string json_data = "{"
        + "\"player_name\":\"" + avatar_name + "\","
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
        // Clean the response text (remove Unicode, escape sequences, markdown, etc.)
        string clean_response = clean_response_text(npc_response);

        // Say response in public (only once - removed duplicate llRegionSayTo)
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

// Clean response text for speaking (comprehensive cleanup)
string clean_response_text(string response)
{
    // Remove Unicode escape sequences (like \ud83d\ude0a for emojis)
    integer pos = llSubStringIndex(response, "\\u");
    while (pos != -1)
    {
        // Find the end of the unicode sequence (4 hex digits after \u)
        if (pos + 5 < llStringLength(response))
        {
            string before = llGetSubString(response, 0, pos - 1);
            string after = llGetSubString(response, pos + 6, -1);
            response = before + after;
        }
        else
        {
            // If incomplete sequence at end, just remove it
            response = llGetSubString(response, 0, pos - 1);
        }
        pos = llSubStringIndex(response, "\\u");
    }

    // Remove other escape sequences like \n, \r, \t
    response = llDumpList2String(llParseString2List(response, ["\\n"], []), " ");
    response = llDumpList2String(llParseString2List(response, ["\\r"], []), "");
    response = llDumpList2String(llParseString2List(response, ["\\t"], []), " ");

    // Remove markdown formatting
    response = llDumpList2String(llParseString2List(response, ["**"], []), "");
    response = llDumpList2String(llParseString2List(response, ["*"], []), "");

    // Trim leading whitespace
    while (llGetSubString(response, 0, 0) == " " && llStringLength(response) > 0)
    {
        response = llGetSubString(response, 1, -1);
    }

    // Trim trailing whitespace
    while (llGetSubString(response, -1, -1) == " " && llStringLength(response) > 0)
    {
        response = llGetSubString(response, 0, -2);
    }

    // Limit length for LSL say function
    if (llStringLength(response) > 2500)
    {
        response = llGetSubString(response, 0, 2496) + "...";
    }

    return response;
}

// Process SL commands from NPC response
process_sl_commands(string commands)
{
    // Commands format: [lookup=obj;llSetText=msg;emote=gesture;anim=action;teleport=x,y,z;notecard=name|content]
    // IMPORTANT: notecard must be last because it can contain semicolons in content

    // Remove outer brackets if present
    if (llGetSubString(commands, 0, 0) == "[")
    {
        commands = llGetSubString(commands, 1, -2);  // Remove [ and ]
    }

    // Check if there's a notecard command (extract it first to avoid semicolon issues)
    string notecard_data = "";
    integer notecard_pos = llSubStringIndex(commands, "notecard=");
    if (notecard_pos != -1)
    {
        // Extract everything after "notecard=" until end
        notecard_data = llGetSubString(commands, notecard_pos + 9, -1);
        // Remove notecard from commands string to process other commands
        commands = llGetSubString(commands, 0, notecard_pos - 1);
        // Remove trailing semicolon if present
        if (llGetSubString(commands, -1, -1) == ";")
        {
            commands = llGetSubString(commands, 0, -2);
        }
    }

    // Split remaining commands by semicolon
    list command_parts = llParseString2List(commands, [";"], []);
    integer i;
    for (i = 0; i < llGetListLength(command_parts); i++)
    {
        string command_part = llList2String(command_parts, i);
        command_part = llStringTrim(command_part, STRING_TRIM);

        // Skip empty parts
        if (command_part == "") jump continue;

        // Check for different command types
        if (llSubStringIndex(command_part, "lookup=") == 0)
        {
            // Lookup command: lookup=object_name
            string lookup_obj = llGetSubString(command_part, 7, -1);
            // Removed llOwnerSay to avoid duplicate output
        }
        else if (llSubStringIndex(command_part, "llSetText=") == 0)
        {
            // llSetText command: llSetText=message
            string text_msg = llGetSubString(command_part, 10, -1);
            text_msg = llUnescapeURL(text_msg);  // Unescape URL encoding if any

            // Convert ~ to \n for line breaks (AI uses ~ as placeholder)
            text_msg = llDumpList2String(llParseString2List(text_msg, ["~"], []), "\n");

            llSetText(text_msg, <1.0, 1.0, 1.0>, 1.0);
        }
        else if (llSubStringIndex(command_part, "emote=") == 0)
        {
            // Emote command: emote=gesture_name
            string emote = llGetSubString(command_part, 6, -1);
            // Could trigger SL animations/gestures here
        }
        else if (llSubStringIndex(command_part, "anim=") == 0)
        {
            // Animation command: anim=animation_name
            string anim = llGetSubString(command_part, 5, -1);
            // Could trigger SL animations here
        }
        else if (llSubStringIndex(command_part, "teleport=") == 0)
        {
            // Teleport command: teleport=x,y,z
            string teleport_coords = llGetSubString(command_part, 9, -1);
            process_teleport(current_toucher, teleport_coords);
        }

        @continue;
    }

    // Process notecard last (if present)
    if (notecard_data != "")
    {
        process_notecard(current_toucher, notecard_data);
    }
}

// Process teleport command
process_teleport(key avatar, string coords)
{
    // Parse coordinates: "x,y,z"
    list coord_parts = llParseString2List(coords, [","], []);
    if (llGetListLength(coord_parts) == 3)
    {
        float x = (float)llList2String(coord_parts, 0);
        float y = (float)llList2String(coord_parts, 1);
        float z = (float)llList2String(coord_parts, 2);

        vector teleport_pos = <x, y, z>;
        llOwnerSay("Teleporting " + llKey2Name(avatar) + " to " + (string)teleport_pos);
        llTeleportAgent(avatar, "", teleport_pos, <0, 0, 0>);
    }
    else
    {
        llOwnerSay("Invalid teleport coordinates: " + coords);
    }
}

// Process notecard command: notecard=NotecardName|Escaped_Content
process_notecard(key avatar, string notecard_data)
{
    // Parse: "NotecardName|Escaped_Content"
    integer pipe_pos = llSubStringIndex(notecard_data, "|");
    if (pipe_pos == -1)
    {
        // Silent fail - malformed notecard
        return;
    }

    string notecard_name = llGetSubString(notecard_data, 0, pipe_pos - 1);
    string escaped_content = llGetSubString(notecard_data, pipe_pos + 1, -1);

    // Unescape the content (reverse of Python's escape)
    string content = unescape_notecard_content(escaped_content);

    // Split content into lines
    list notecard_lines = llParseString2List(content, ["\n"], []);

    // Create the notecard
    osMakeNotecard(notecard_name, notecard_lines);

    // Give the notecard to the player
    llGiveInventory(avatar, notecard_name);

    // Remove from object inventory after giving
    llRemoveInventory(notecard_name);
}

// Unescape notecard content (reverse of Python escaping)
// Python escapes: \\ → \\, " → \", \n → \n
string unescape_notecard_content(string escaped)
{
    string result = "";
    integer i = 0;
    integer len = llStringLength(escaped);

    while (i < len)
    {
        string char = llGetSubString(escaped, i, i);

        if (char == "\\" && i + 1 < len)
        {
            string next_char = llGetSubString(escaped, i + 1, i + 1);
            if (next_char == "n")
            {
                result += "\n";
                i += 2;
            }
            else if (next_char == "\"")
            {
                result += "\"";
                i += 2;
            }
            else if (next_char == "\\")
            {
                result += "\\";
                i += 2;
            }
            else
            {
                result += char;
                i += 1;
            }
        }
        else
        {
            result += char;
            i += 1;
        }
    }

    return result;
}

// Function to end the current conversation
end_conversation()
{
    if (IS_CONVERSING)
    {
        llOwnerSay("Ending conversation with " + current_toucher_name);

        // Notify the backend that the avatar is leaving (save conversation)
        if (current_toucher != NULL_KEY)
        {
            call_leave_endpoint(current_toucher_name);
        }

        // Remove the listen handle
        if (listen_handle != -1)
        {
            llListenRemove(listen_handle);
            listen_handle = -1;
        }

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

        // Update display
        llSetText("Tocca per parlare\ncon " + NPC_NAME + "\n(Touch to talk)", <1.0, 1.0, 0.5>, 1.0);
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
// Check server health during initialization
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
    if (version != "")
    {
        llSetText("Eldoria v" + version + "\n" + NPC_NAME + "\nVerifying NPC...", <1.0, 1.0, 0.0>, 1.0);
        llOwnerSay("✓ Server health check passed. Version: " + version);
    }
    else
    {
        llSetText(NPC_NAME + "\nVerifying\nNPC...", <1.0, 1.0, 0.5>, 1.0);
        llOwnerSay("✓ Server health check passed (version unknown)");
    }

    // Now verify NPC exists in database
    verify_npc_exists();
}

// Verify NPC exists and check capabilities
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
        string has_teleport = extract_json_value(response_body, "has_teleport");
        string has_llsettext = extract_json_value(response_body, "has_llsettext");
        string has_notecard = extract_json_value(response_body, "has_notecard");

        // Build capabilities string
        string capabilities = "";
        if (has_teleport == "true") capabilities += "✓ Teleport | ";
        if (has_llsettext == "true") capabilities += "✓ Text | ";
        if (has_notecard == "true") capabilities += "✓ Notecard";

        // Remove trailing " | " if present
        if (llGetSubString(capabilities, -2, -1) == "| ")
        {
            capabilities = llGetSubString(capabilities, 0, -4);
        }

        llSetText("✓ " + NPC_NAME + "\n(" + CURRENT_AREA + ")\n[" + capabilities + "]\nTocca per parlare", <0.0, 1.0, 0.0>, 1.0);
        llOwnerSay("✓ NPC configuration verified!");
        llOwnerSay("  NPC: " + NPC_NAME + " in area: " + CURRENT_AREA);
        llOwnerSay("  Capabilities: [" + capabilities + "]");
    }
    else
    {
        string error = extract_json_value(response_body, "error");
        llSetText("✗ NPC not found\n" + NPC_NAME + "\n(" + CURRENT_AREA + ")", <1.0, 0.0, 0.0>, 1.0);
        llOwnerSay("✗ ERROR: NPC not found in database");
        llOwnerSay("  Requested: " + NPC_NAME + " in area: " + CURRENT_AREA);
        if (error != "")
        {
            llOwnerSay("  Error message: " + error);
        }
    }
}
