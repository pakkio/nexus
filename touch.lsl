// Simplified Touch-Activated NPC Dialogue System
// Uses /sense endpoint for simple LSL-friendly responses
// Activated by touch - only listens to the toucher during conversation
// Maintains dialogue state with the toucher until they leave range or touch again
// Resets automatically after 5 minutes of inactivity

// Configuration
string SERVER_URL = "http://localhost:5000";  // Your Nexus server URL
string NPC_NAME;                              // Name of this NPC (will be set to object name)
string CURRENT_AREA = "DefaultArea";          // Area name for context

// State variables
key current_toucher = NULL_KEY;       // Key of the avatar currently in conversation
string current_toucher_name = "";     // Name of the current toucher
integer listen_handle = -1;           // Handle for the listen event
integer IS_CONVERSING = FALSE;        // Flag to track if in active conversation
integer TIMEOUT_SECONDS = 300;        // 5 minutes in seconds (300 seconds)

// HTTP request tracking
key chat_request_id;
key leave_request_id;

default
{
    state_entry()
    {
        // Get the object name to use as NPC name
        NPC_NAME = llGetObjectName();

        // Set initial display text
        llSetText("Tocca per parlare con " + NPC_NAME + "\n(Touch to talk)", <1.0, 1.0, 0.5>, 1.0);

        // Initialize conversation state
        current_toucher = NULL_KEY;
        current_toucher_name = "";
        IS_CONVERSING = FALSE;

        llOwnerSay("Touch-activated NPC initialized for " + NPC_NAME + ". Waiting for touch.");
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
            llSetText("Sto parlando con " + toucher_name + "\n(Conversing)", <0.0, 1.0, 0.0>, 1.0);
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

            // Call the chat API to get NPC response
            call_message_endpoint(message, name);
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
        // Handle chat responses
        if (request_id == chat_request_id && IS_CONVERSING)
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

    chat_request_id = llHTTPRequest(SERVER_URL + "/sense", http_options, json_data);
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

        // Speak to the current toucher
        llRegionSayTo(current_toucher, 0, clean_response);

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
        llOwnerSay("Processing SL commands: " + sl_commands);
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
    // Commands format: [lookup=obj;llSetText=msg;emote=gesture;anim=action;teleport=x,y,z;notecard=name|content;...]
    // Remove outer brackets if present
    if (llGetSubString(commands, 0, 0) == "[")
    {
        commands = llGetSubString(commands, 1, -2);  // Remove [ and ]
    }

    // Split by semicolon to get individual commands
    list command_parts = llParseString2List(commands, [";"], []);
    integer i;
    for (i = 0; i < llGetListLength(command_parts); i++)
    {
        string command_part = llList2String(command_parts, i);
        command_part = llStringTrim(command_part, STRING_TRIM);

        // Check for different command types
        if (llSubStringIndex(command_part, "lookup=") == 0)
        {
            // Lookup command: lookup=object_name
            string lookup_obj = llGetSubString(command_part, 7, -1);
            llOwnerSay("Lookup object: " + lookup_obj);
        }
        else if (llSubStringIndex(command_part, "llSetText=") == 0)
        {
            // llSetText command: llSetText=message
            string text_msg = llGetSubString(command_part, 10, -1);
            text_msg = llUnescapeURL(text_msg);  // Unescape URL encoding if any
            llSetText(text_msg, <1.0, 1.0, 1.0>, 1.0);
            llOwnerSay("Setting floating text: " + text_msg);
        }
        else if (llSubStringIndex(command_part, "emote=") == 0)
        {
            // Emote command: emote=gesture_name
            string emote = llGetSubString(command_part, 6, -1);
            llOwnerSay("Emote: " + emote);
            // Could trigger SL animations/gestures here
        }
        else if (llSubStringIndex(command_part, "anim=") == 0)
        {
            // Animation command: anim=animation_name
            string anim = llGetSubString(command_part, 5, -1);
            llOwnerSay("Animation: " + anim);
            // Could trigger SL animations here
        }
        else if (llSubStringIndex(command_part, "teleport=") == 0)
        {
            // Teleport command: teleport=x,y,z
            string teleport_coords = llGetSubString(command_part, 9, -1);
            process_teleport(current_toucher, teleport_coords);
        }
        else if (llSubStringIndex(command_part, "notecard=") == 0)
        {
            // Notecard command: notecard=name|content
            string notecard_data = llGetSubString(command_part, 9, -1);
            process_notecard(current_toucher, notecard_data);
        }
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
        llOwnerSay("[ERROR] Notecard command malformed: no pipe separator");
        return;
    }

    string notecard_name = llGetSubString(notecard_data, 0, pipe_pos - 1);
    string escaped_content = llGetSubString(notecard_data, pipe_pos + 1, -1);

    llOwnerSay("[NOTECARD] Creating notecard '" + notecard_name + "' for " + llKey2Name(avatar));
    llOwnerSay("[NOTECARD] Content length: " + (string)llStringLength(escaped_content) + " chars");

    // Unescape the content (reverse of Python's escape)
    string content = unescape_notecard_content(escaped_content);

    // Split content into lines
    list notecard_lines = llParseString2List(content, ["\n"], []);

    // Create the notecard
    try
    {
        llOwnerSay("[NOTECARD] Calling osMakeNotecard with " + (string)llGetListLength(notecard_lines) + " lines");
        osMakeNotecard(notecard_name, notecard_lines);

        // Give the notecard to the player
        llGiveInventory(avatar, notecard_name);
        llOwnerSay("[NOTECARD] ✓ Notecard '" + notecard_name + "' given to " + llKey2Name(avatar));

        // Optional: Remove from object inventory after giving
        llRemoveInventory(notecard_name);
    }
    catch(exception e)
    {
        llOwnerSay("[ERROR] Failed to create/give notecard: " + llGetExceptionString(e));
    }
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

    // Limit length for LSL say function
    if (llStringLength(response) > 1000) {
        response = llGetSubString(response, 0, 996) + "...";
    }

    return response;
}
