// LSL Script: NPC Notecard Receiver and Giver - Refactored with Best Practices
// Receives notecard commands from NPC responses and creates/gives notecards to players
// Handles commands in format: [notecard=NotecardName|NotecardContent]
// Uses osMakeNotecard() to create notecards efficiently
// Incorporates state management, timeout handling, and improved error handling

// Configuration
string NOTECARD_VERSION = "v1.1";
integer TIMEOUT_SECONDS = 300;  // 5 minutes inactivity timeout
integer IS_ACTIVE = FALSE;
key current_player = NULL_KEY;
string current_player_name = "";

// Utility function to extract JSON value with escape handling
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

    return "";
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

// Unescape LSL-encoded notecard content
string UnescapeNotecardContent(string escaped) {
    // LSL escaping uses: \n for newline, \", \\
    // Reverse the process to restore original content

    string result = "";
    integer i = 0;
    integer len = llStringLength(escaped);

    while (i < len) {
        string char = llGetSubString(escaped, i, i);

        if (char == "\\" && i + 1 < len) {
            string next_char = llGetSubString(escaped, i + 1, i + 1);
            if (next_char == "n") {
                result += "\n";
                i += 2;
            } else if (next_char == "\"") {
                result += "\"";
                i += 2;
            } else if (next_char == "\\") {
                result += "\\";
                i += 2;
            } else {
                result += char;
                i += 1;
            }
        } else {
            result += char;
            i += 1;
        }
    }

    return result;
}

// Parse notecard command from SL message
list SplitNotecardCommand(string command) {
    // Parse format: notecard=Name|Content
    // Extract name and content from the command string

    integer pipe_pos = llSubStringIndex(command, "|");
    if (pipe_pos == -1) {
        llOwnerSay("[DEBUG] No pipe found in notecard command: " + command);
        return [];
    }

    string notecard_part = llGetSubString(command, 0, pipe_pos - 1);
    string content_part = llGetSubString(command, pipe_pos + 1, -1);

    // Extract name from "notecard=Name" format
    integer eq_pos = llSubStringIndex(notecard_part, "=");
    if (eq_pos == -1) {
        llOwnerSay("[DEBUG] No equals sign found in notecard part: " + notecard_part);
        return [];
    }

    string notecard_name = llGetSubString(notecard_part, eq_pos + 1, -1);

    llOwnerSay("[DEBUG] Parsed notecard: name='" + notecard_name + "', content_len=" + (string)llStringLength(content_part));
    return [notecard_name, content_part];
}

// Create and give notecard to player
CreateAndGiveNotecard(key player_id, string player_name, string notecard_name, string content) {
    // Unescape the content from LSL encoding
    string unescaped_content = UnescapeNotecardContent(content);

    llOwnerSay("[NOTECARD] Creating notecard '" + notecard_name + "' for " + player_name + " (content: " + (string)llStringLength(unescaped_content) + " chars)");

    // Use osMakeNotecard to create the notecard
    // This is a high-threat OSSL function but necessary for persistent notecard creation
    // Format: osMakeNotecard(string notecardName, list contents)

    list notecard_contents = [];

    // Split content into manageable lines to avoid string limits
    list lines = llParseString2List(unescaped_content, ["\n"], []);
    integer line_count = llGetListLength(lines);

    for (integer i = 0; i < line_count; i++) {
        string line = llList2String(lines, i);
        notecard_contents += [line + "\n"];
    }

    // Create the notecard
    try {
        llOwnerSay("[NOTECARD] Calling osMakeNotecard with " + (string)line_count + " lines");
        osMakeNotecard(notecard_name, notecard_contents);

        // Give the notecard to the player
        llOwnerSay("[NOTECARD] Giving notecard to player");
        llGiveInventory(player_id, notecard_name);

        // Clean up the notecard from object inventory after giving
        llOwnerSay("[NOTECARD] Cleaning up notecard from inventory");
        llRemoveInventory(notecard_name);

        llRegionSayTo(player_id, 0, "Hai ricevuto: " + notecard_name);
        llOwnerSay("[SUCCESS] Notecard '" + notecard_name + "' successfully created and given to " + player_name);
    }
    catch(exception e) {
        llOwnerSay("[ERROR] Failed to create notecard '" + notecard_name + "': " + llGetExceptionString(e));
        llRegionSayTo(player_id, 0, "Scusa, non riesco a creare il documento in questo momento.");
    }
}

// End notecard transaction
end_notecard_session()
{
    if (IS_ACTIVE)
    {
        llOwnerSay("[SESSION] Ending notecard session with " + current_player_name);

        // Stop the timeout timer
        llSetTimerEvent(0.0);

        // Reset state
        current_player = NULL_KEY;
        current_player_name = "";
        IS_ACTIVE = FALSE;

        llOwnerSay("[SESSION] Notecard handler ready for next session");
    }
}

// Main event handler
default
{
    state_entry()
    {
        llSetObjectDesc("NPC Notecard Handler " + NOTECARD_VERSION);
        llSetText("Notecard Handler Ready", <1.0, 1.0, 0.0>, 1.0);
        llOwnerSay("[INIT] NPC Notecard Receiver initialized. Using osMakeNotecard for persistent notecards.");
        llOwnerSay("[INFO] Listening for notecard commands on region say");

        // Initialize state
        IS_ACTIVE = FALSE;
        current_player = NULL_KEY;
        current_player_name = "";
    }

    on_rez(integer start_param)
    {
        llResetScript();
    }

    touch_start(integer num_detected)
    {
        key toucher = llDetectedKey(0);
        string toucher_name = llDetectedName(0);

        llRegionSayTo(toucher, 0, "Notecard Handler active. Waiting for notecard commands...");
        llOwnerSay("[TOUCH] Touched by " + toucher_name);
    }

    // Listen for notecard commands from NPC responses via region say
    listen(integer channel, string name, key id, string message)
    {
        // Parse incoming notecard command
        // Format: [notecard=NotecardName|NotecardContent...]

        if (llSubStringIndex(message, "notecard=") == -1) {
            return;  // Not a notecard command
        }

        llOwnerSay("[LISTEN] Received message with notecard command from " + name);

        // Extract the notecard command from the message
        integer start = llSubStringIndex(message, "notecard=");
        if (start == -1) {
            llOwnerSay("[ERROR] Could not find notecard= in message");
            return;
        }

        string notecard_cmd = llGetSubString(message, start, -1);

        // Parse the command
        list parts = SplitNotecardCommand(notecard_cmd);
        if (llGetListLength(parts) != 2) {
            llOwnerSay("[ERROR] Malformed notecard command: could not parse " + notecard_cmd);
            return;  // Malformed command
        }

        string notecard_name = llList2String(parts, 0);
        string notecard_content = llList2String(parts, 1);

        // Get the player ID (use current toucher or owner as fallback)
        key player_id = current_player != NULL_KEY ? current_player : llGetOwner();
        string player_name = current_player_name != "" ? current_player_name : llGetObjectName();

        // Set active session
        IS_ACTIVE = TRUE;
        current_player = player_id;
        current_player_name = player_name;

        // Set timeout for session cleanup
        llSetTimerEvent(TIMEOUT_SECONDS);

        // Create and give the notecard
        CreateAndGiveNotecard(player_id, player_name, notecard_name, notecard_content);

        // Schedule session cleanup
        llSetTimerEvent(30.0);  // Cleanup timer: 30 seconds after notecard given
    }

    timer()
    {
        if (IS_ACTIVE)
        {
            llOwnerSay("[TIMEOUT] Notecard session timeout for " + current_player_name);
            end_notecard_session();
        }
    }
}

