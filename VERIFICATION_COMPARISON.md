# Configuration Verification Comparison

## touch.lsl vs lsl_touch_npc_script.lsl

### Static Configuration Validation ✅

Both scripts perform the same static checks:

| Check | touch.lsl | lsl_touch_npc_script.lsl |
|-------|-----------|-------------------------|
| SERVER_URL not empty | ✅ Yes | ✅ Yes |
| SERVER_URL starts with "http" | ✅ Yes | ✅ Yes |
| Object name has "." separator | ✅ Yes | ✅ Yes |
| NPC name not empty | ✅ Yes | ✅ Yes |
| Area name not empty | ✅ Yes | ✅ Yes |
| Error messages provided | ✅ Yes | ✅ Yes |

---

### Dynamic Verification (Runtime) ❌ vs ✅

**lsl_touch_npc_script.lsl** performs additional runtime verification that **touch.lsl lacks**:

#### 1. Server Health Check
```lsl
check_server_health()
{
    // Makes GET request to /health endpoint
    // Verifies server is running and responsive
    // Extracts version information
}
```

**Purpose**: Confirms backend server is accessible and running
**Endpoint**: `/health`
**Response**: `{"version": "X.X.X", ...}`

#### 2. NPC Verification
```lsl
verify_npc_exists()
{
    // Makes POST request to /api/npc/verify with NPC name and area
    // Confirms NPC exists in database
    // Checks NPC capabilities (teleport, llSetText, etc.)
}
```

**Purpose**: Confirms NPC is properly configured in backend
**Endpoint**: `/api/npc/verify`
**Request**:
```json
{
    "npc_name": "Elira",
    "area": "Forest"
}
```

**Response**:
```json
{
    "found": "true",
    "npc_name": "Elira",
    "area": "Forest",
    "has_teleport": "true",
    "has_llsettext": "true",
    "has_notecard": "true"
}
```

#### 3. Capability Detection
```lsl
handle_npc_verification_response(string response_body)
{
    string found = extract_json_value(response_body, "found");
    string has_teleport = extract_json_value(response_body, "has_teleport");
    string has_llsettext = extract_json_value(response_body, "has_llsettext");
    // ... display capabilities in llSetText
}
```

**Purpose**: Detects which features are available for this NPC
**Capabilities checked**:
- `has_teleport` - NPC can teleport players
- `has_llsettext` - NPC can display floating text
- `has_notecard` - NPC can deliver notecards

---

## Status Display Progression

### lsl_touch_npc_script.lsl

**Initialization Status**:
```
1. Script starts
   ↓
2. "Verifying NPC..." (yellow text)
   ↓
3. check_server_health() called
   ↓
4. "Eldoria v1.2.3 - Elira\nVerifying NPC..." (yellow text)
   ↓
5. verify_npc_exists() called
   ↓
6. "✓ Elira (Forest)\n[✓ Teleport | ✓ Text | ✓ Notecard]" (green text)
   ↓
7. Ready for interaction
```

### touch.lsl

**Initialization Status**:
```
1. Script starts
   ↓
2. Configuration parsed
   ↓
3. "Tocca per parlare con Elira\n(Touch to talk)" (yellow text)
   ↓
4. Ready for interaction (NO verification!)
```

---

## What touch.lsl is Missing

### Missing Runtime Verification

1. **No server health check** - Can't detect if backend is down
2. **No NPC existence verification** - Can't confirm NPC is in database
3. **No capability detection** - Can't know which features are enabled
4. **No version display** - Can't show Eldoria version

### Impact

| Scenario | touch.lsl | lsl_touch_npc_script.lsl |
|----------|-----------|-------------------------|
| Server down on startup | Shows ready, but fails on first touch | Shows "Server unreachable" |
| NPC not in database | Shows ready, but fails on first touch | Shows "NPC not found" |
| Teleport disabled for NPC | Shows ready, but teleport fails silently | Shows "Teleport unavailable" |
| First touch attempts API call | ✅ Works but slow (waits for response) | ✅ Knows API is good immediately |

---

## Recommended Fix for touch.lsl

Add to `state_entry()` after configuration validation:

```lsl
// Verify server health and NPC configuration
check_server_health();
```

Add new functions:

```lsl
check_server_health()
{
    list http_options = [
        HTTP_METHOD, "GET",
        HTTP_BODY_MAXLENGTH, 16384,
        HTTP_VERIFY_CERT, FALSE
    ];

    health_request_id = llHTTPRequest(SERVER_URL + "/health", http_options, "");
}

handle_health_response(string response_body)
{
    string version = extract_json_value(response_body, "version");
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

handle_npc_verification_response(string response_body)
{
    string found = extract_json_value(response_body, "found");

    if (found == "true")
    {
        string has_teleport = extract_json_value(response_body, "has_teleport");
        string has_llsettext = extract_json_value(response_body, "has_llsettext");
        string has_notecard = extract_json_value(response_body, "has_notecard");

        string capabilities = "";
        if (has_teleport == "true") capabilities += "✓ Teleport | ";
        if (has_llsettext == "true") capabilities += "✓ Text | ";
        if (has_notecard == "true") capabilities += "✓ Notecard";

        llSetText("✓ " + NPC_NAME + " (" + CURRENT_AREA + ")\n[" + capabilities + "]", <0.0, 1.0, 0.0>, 1.0);
        llOwnerSay("✓ NPC configuration verified!");
    }
    else
    {
        string npc_not_found = extract_json_value(response_body, "error");
        llSetText("✗ NPC not found in database\n" + NPC_NAME + " (" + CURRENT_AREA + ")", <1.0, 0.0, 0.0>, 1.0);
        llOwnerSay("✗ ERROR: NPC not found: " + npc_not_found);
    }
}
```

Update `http_response()` handler to call appropriate handler based on request ID:

```lsl
http_response(key request_id, integer status, list metadata, string body)
{
    if (request_id == health_request_id)
    {
        if (status == 200)
            handle_health_response(body);
        else
            llOwnerSay("✗ Server health check failed: " + (string)status);
    }
    else if (request_id == npc_verify_request_id)
    {
        if (status == 200)
            handle_npc_verification_response(body);
        else
            llOwnerSay("✗ NPC verification failed: " + (string)status);
    }
    // ... rest of chat/leave handlers
}
```

---

## Summary

- **touch.lsl**: ✅ Has static configuration validation (object name format, server URL format)
- **touch.lsl**: ❌ Missing dynamic verification (server health, NPC existence, capabilities)
- **lsl_touch_npc_script.lsl**: ✅ Has both static and dynamic verification

**Recommendation**: Add the runtime verification to `touch.lsl` to match the robustness of the reference script.

---

*Analysis Date: 2025-10-20*
