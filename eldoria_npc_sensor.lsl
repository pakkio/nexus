// Eldoria NPC Sensor Script with Chat Integration
// Detects avatars within 6m, calls /sense and /unsense endpoints
// Listens to public chat and integrates with /chat endpoint

// Configuration
string SERVER_URL = "http://your-server.com"; // Replace with your actual server URL
string NPC_NAME = "YourNPCName"; // Replace with actual NPC name
string CURRENT_AREA = "YourArea"; // Replace with current area name
float SENSOR_RANGE = 6.0; // Detection range in meters
integer LISTEN_CHANNEL = 0; // Public chat channel
float SENSOR_REPEAT = 2.0; // Sensor repeat interval in seconds

// State variables
list detected_avatars = []; // List of currently detected avatar keys
integer listen_handle = -1; // Listen handle for chat monitoring
string current_avatar_name = ""; // Name of currently detected avatar

// HTTP request tracking
key sense_request_id;
key unsense_request_id;
key chat_request_id;

default
{
    state_entry()
    {
        llSetText("Eldoria NPC - " + NPC_NAME + "\nSensing avatars...", <0.8, 1.0, 0.8>, 1.0);
        
        // Start sensor scanning for avatars
        llSensorRepeat("", "", AGENT, SENSOR_RANGE, PI, SENSOR_REPEAT);
        
        // Start listening to public chat
        if (listen_handle != -1) {
            llListenRemove(listen_handle);
        }
        listen_handle = llListen(LISTEN_CHANNEL, "", "", "");
        
        llOwnerSay("Eldoria NPC initialized. Scanning for avatars within " + (string)SENSOR_RANGE + "m");
    }
    
    sensor(integer num_detected)
    {
        list new_avatars = [];
        
        // Build list of currently detected avatars
        integer i;
        for (i = 0; i < num_detected; i++)
        {
            key avatar_key = llDetectedKey(i);
            string avatar_name = llDetectedName(i);
            new_avatars += [avatar_key];
            
            // Check if this is a newly detected avatar
            if (llListFindList(detected_avatars, [avatar_key]) == -1)
            {
                // New avatar detected - call /sense endpoint
                call_sense_endpoint(avatar_name);
                current_avatar_name = avatar_name;
                llOwnerSay("Avatar detected: " + avatar_name + " (" + (string)avatar_key + ")");
            }
        }
        
        // Check for avatars that are no longer detected
        for (i = 0; i < llGetListLength(detected_avatars); i++)
        {
            key old_avatar = llList2Key(detected_avatars, i);
            if (llListFindList(new_avatars, [old_avatar]) == -1)
            {
                // Avatar left - call /unsense endpoint
                string avatar_name = get_avatar_name_by_key(old_avatar);
                call_unsense_endpoint(avatar_name);
                llOwnerSay("Avatar left: " + avatar_name + " (" + (string)old_avatar + ")");
                
                // Clear current avatar name if this was the current one
                if (avatar_name == current_avatar_name) {
                    current_avatar_name = "";
                }
            }
        }
        
        // Update the detected avatars list
        detected_avatars = new_avatars;
        
        // Update floating text with current status
        update_status_text();
    }
    
    no_sensor()
    {
        // No avatars detected - clear all if we had any
        if (llGetListLength(detected_avatars) > 0)
        {
            integer i;
            for (i = 0; i < llGetListLength(detected_avatars); i++)
            {
                key avatar_key = llList2Key(detected_avatars, i);
                string avatar_name = get_avatar_name_by_key(avatar_key);
                call_unsense_endpoint(avatar_name);
                llOwnerSay("Avatar left range: " + avatar_name);
            }
            detected_avatars = [];
            current_avatar_name = "";
            update_status_text();
        }
    }
    
    listen(integer channel, string name, key id, string message)
    {
        // Only process chat from detected avatars on public channel
        if (channel == LISTEN_CHANNEL && llListFindList(detected_avatars, [id]) != -1)
        {
            string avatar_name = name;
            llOwnerSay("Chat from " + avatar_name + ": " + message);
            
            // Call /chat endpoint with the message
            call_chat_endpoint(message, avatar_name);
        }
    }
    
    http_response(key request_id, integer status, list metadata, string body)
    {
        if (status == 200)
        {
            if (request_id == sense_request_id)
            {
                llOwnerSay("Sense request successful");
                // Parse response and potentially update NPC state
                handle_sense_response(body);
            }
            else if (request_id == unsense_request_id)
            {
                llOwnerSay("Unsense request successful");
            }
            else if (request_id == chat_request_id)
            {
                llOwnerSay("Chat request successful");
                // Parse and speak the NPC response
                handle_chat_response(body);
            }
        }
        else
        {
            llOwnerSay("HTTP Error " + (string)status + ": " + body);
        }
    }
    
    touch_start(integer total_number)
    {
        key toucher = llDetectedKey(0);
        string toucher_name = llDetectedName(0);
        
        llOwnerSay("Touched by: " + toucher_name);
        llSay(0, "Hello " + toucher_name + "! I am " + NPC_NAME + ", an Eldoria NPC. Move within " + (string)SENSOR_RANGE + "m to interact with me through chat.");
    }
}

// Function to call /sense endpoint
call_sense_endpoint(string avatar_name)
{
    string json_data = "{"
        + "\"name\":\"" + avatar_name + "\","
        + "\"npc\":\"" + NPC_NAME + "\""
        + "}";
    
    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 8192
    ];
    
    sense_request_id = llHTTPRequest(SERVER_URL + "/sense", http_options, json_data);
}

// Function to call /unsense endpoint  
call_unsense_endpoint(string avatar_name)
{
    string json_data = "{"
        + "\"name\":\"" + avatar_name + "\","
        + "\"npc\":\"" + NPC_NAME + "\""
        + "}";
    
    list http_options = [
        HTTP_METHOD, "POST",
        HTTP_MIMETYPE, "application/json",
        HTTP_BODY_MAXLENGTH, 8192
    ];
    
    unsense_request_id = llHTTPRequest(SERVER_URL + "/unsense", http_options, json_data);
}

// Function to call /chat endpoint
call_chat_endpoint(string message, string avatar_name)
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
        HTTP_BODY_MAXLENGTH, 8192
    ];
    
    chat_request_id = llHTTPRequest(SERVER_URL + "/api/chat", http_options, json_data);
}

// Handle /sense endpoint response
handle_sense_response(string response_body)
{
    // Parse JSON response and potentially extract greeting message
    // For now, just log the response
    llOwnerSay("Sense response: " + llGetSubString(response_body, 0, 200) + "...");
    
    // You could parse the JSON here to extract and speak any greeting message
    // from the "message" field in the response
}

// Handle /chat endpoint response
handle_chat_response(string response_body)
{
    // Parse JSON response to extract NPC response
    string npc_response = extract_json_value(response_body, "npc_response");
    
    if (npc_response != "")
    {
        // Clean up the response (remove LSL commands, format for speech)
        string clean_response = clean_response_text(npc_response);
        
        // Speak the response in public chat
        if (llStringLength(clean_response) > 0)
        {
            llSay(0, clean_response);
        }
        
        // Process any LSL commands in the response
        process_lsl_commands(npc_response);
    }
    else
    {
        llOwnerSay("No NPC response received");
    }
}

// Utility function to get avatar name by key (simplified)
string get_avatar_name_by_key(key avatar_key)
{
    // In a real implementation, you might want to maintain a key->name mapping
    // For now, return a placeholder
    return "Avatar_" + (string)avatar_key;
}

// Update floating text status
update_status_text()
{
    integer num_detected = llGetListLength(detected_avatars);
    string status_text = "Eldoria NPC - " + NPC_NAME + "\n";
    
    if (num_detected == 0)
    {
        status_text += "No avatars in range";
    }
    else if (num_detected == 1)
    {
        status_text += "1 avatar in range: " + current_avatar_name;
    }
    else
    {
        status_text += (string)num_detected + " avatars in range";
    }
    
    llSetText(status_text, <0.8, 1.0, 0.8>, 1.0);
}

// Escape JSON string characters
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

// Extract value from JSON string (simple implementation)
string extract_json_value(string json, string key)
{
    string search_key = "\"" + key + "\":\"";
    integer start_pos = llSubStringIndex(json, search_key);
    
    if (start_pos == -1) return "";
    
    start_pos += llStringLength(search_key);
    integer end_pos = llSubStringIndex(llGetSubString(json, start_pos, -1), "\"");
    
    if (end_pos == -1) return "";
    
    return llGetSubString(json, start_pos, start_pos + end_pos - 1);
}

// Clean response text for speaking
string clean_response_text(string response)
{
    // Remove LSL command tags like [emote=greet], [anim=sit], etc.
    response = llDumpList2String(llParseString2List(response, ["["], []), "");
    response = llDumpList2String(llParseString2List(response, ["]"], []), "");
    
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

// Process LSL commands from response
process_lsl_commands(string response)
{
    // Look for and process commands like [emote=greet], [anim=sit], [llSetText=message]
    
    // Process emote commands
    integer emote_pos = llSubStringIndex(response, "[emote=");
    if (emote_pos != -1) {
        integer start = emote_pos + 7; // length of "[emote="
        integer end = llSubStringIndex(llGetSubString(response, start, -1), "]");
        if (end != -1) {
            string emote = llGetSubString(response, start, start + end - 1);
            llOwnerSay("Would trigger emote: " + emote);
            // In a real implementation, you would trigger the actual gesture here
        }
    }
    
    // Process animation commands
    integer anim_pos = llSubStringIndex(response, "[anim=");
    if (anim_pos != -1) {
        integer start = anim_pos + 6; // length of "[anim="
        integer end = llSubStringIndex(llGetSubString(response, start, -1), "]");
        if (end != -1) {
            string animation = llGetSubString(response, start, start + end - 1);
            llOwnerSay("Would trigger animation: " + animation);
            // In a real implementation, you would start the animation here
        }
    }
    
    // Process llSetText commands
    integer text_pos = llSubStringIndex(response, "[llSetText=");
    if (text_pos != -1) {
        integer start = text_pos + 10; // length of "[llSetText="
        integer end = llSubStringIndex(llGetSubString(response, start, -1), "]");
        if (end != -1) {
            string text_message = llGetSubString(response, start, start + end - 1);
            llSetText(text_message, <1.0, 1.0, 0.0>, 1.0);
            llOwnerSay("Updated floating text: " + text_message);
        }
    }
    
    // Process lookup commands
    integer lookup_pos = llSubStringIndex(response, "[lookup=");
    if (lookup_pos != -1) {
        integer start = lookup_pos + 8; // length of "[lookup="
        integer end = llSubStringIndex(llGetSubString(response, start, -1), "]");
        if (end != -1) {
            string object_name = llGetSubString(response, start, start + end - 1);
            llOwnerSay("Would lookup object: " + object_name);
            // In a real implementation, you could highlight or reference the object
        }
    }
}