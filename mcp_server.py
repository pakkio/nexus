"""
MCP server wrapping the Nexus REST API as MCP tools.

Mounted into the same ASGI app as the Flask REST API (see app.py's __main__
block) so it's served from the same port (NEXUS_PORT, 5000 by default) rather
than opening a second port. Every tool is a thin wrapper that issues a
loopback HTTP call to the corresponding Flask route, carrying the same
Bearer token app.py's own require_bearer_auth() expects - there is exactly
one implementation of each endpoint's behavior (app.py's), never a second
copy of the logic living here.

The /mcp endpoint itself is separately gated on the same Bearer token via
BearerAuthMiddleware below, so an MCP client needs the token before it can
even open a session, not just before individual tool calls succeed.
"""

import contextlib
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

# Same default/env-var as app.py's NEXUS_AUTH_TOKEN - kept as a separate
# constant (not imported from app) so this module has no import-time
# dependency on app.py, avoiding a circular import (app.py imports this
# module late, after it has already defined NEXUS_AUTH_TOKEN and app).
NEXUS_AUTH_TOKEN = os.environ.get("NEXUS_AUTH_TOKEN", "pakkio 62")
_NEXUS_PORT = int(os.environ.get("NEXUS_PORT", 5000))
_BASE_URL = f"http://127.0.0.1:{_NEXUS_PORT}"

mcp = MCPServer(
    "nexus",
    version="1.0.0",
    instructions=(
        "Tools wrapping the Nexus RPG REST API: NPC dialogue (sense/chat/leave_npc), "
        "player state/profile/inventory/conversation history, and game data (areas/npcs/"
        "storyboard). Every tool is a thin wrapper around the equivalent REST endpoint - "
        "GET /api lists the full endpoint catalog, and call_endpoint is a generic "
        "passthrough for anything not wrapped explicitly below."
    ),
)


def _call(
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Loopback call to the Flask REST API, carrying the same bearer token it requires."""
    headers = {"Authorization": f"Bearer {NEXUS_AUTH_TOKEN}"}
    try:
        resp = httpx.request(
            method, f"{_BASE_URL}{path}", json=json_body, params=params,
            headers=headers, timeout=30.0,
        )
    except httpx.RequestError as e:
        return {"error": f"request to {path} failed: {e}"}
    try:
        body = resp.json()
    except ValueError:
        body = {"raw": resp.text}
    return {"status": resp.status_code, "body": body}


@mcp.tool()
def health() -> dict:
    """Check the Nexus API's health/status."""
    return _call("GET", "/health")


@mcp.tool()
def get_version() -> dict:
    """Get the Nexus API version and changelog."""
    return _call("GET", "/version")


@mcp.tool()
def list_areas() -> dict:
    """List all game areas."""
    return _call("GET", "/api/game/areas")


@mcp.tool()
def list_npcs(area: str | None = None) -> dict:
    """List NPCs, optionally filtered to one area (case-insensitive)."""
    return _call("GET", "/api/game/npcs", params={"area": area} if area else None)


@mcp.tool()
def get_storyboard() -> dict:
    """Get the game's storyboard/setting text."""
    return _call("GET", "/api/game/storyboard")


@mcp.tool()
def verify_npc(npc_name: str, area: str) -> dict:
    """Check whether an NPC exists in a given area, and which capabilities it has
    (teleport, llSetText, notecard)."""
    return _call("POST", "/api/npc/verify", json_body={"npc_name": npc_name, "area": area})


@mcp.tool()
def sense(player_name: str, npc_name: str, area: str) -> dict:
    """Announce a player's arrival to an NPC and get its greeting - the same call the
    in-world 'brain' script makes the moment a player first touches an NPC."""
    return _call(
        "POST", "/sense",
        json_body={"name": player_name, "npcname": npc_name, "area": area},
    )


@mcp.tool()
def chat(message: str, player_name: str, npc_name: str | None = None, area: str | None = None) -> dict:
    """Send a chat message to an NPC (continuing whatever conversation is already open
    for this player, or starting one if npc_name/area are given) and get its reply."""
    body: dict[str, Any] = {"message": message, "player_name": player_name}
    if npc_name:
        body["npc_name"] = npc_name
    if area:
        body["area"] = area
    return _call("POST", "/api/chat", json_body=body)


@mcp.tool()
def leave_npc(player_name: str, npc_name: str, area: str) -> dict:
    """End a conversation with an NPC (equivalent to the player walking away)."""
    return _call(
        "POST", "/api/leave_npc",
        json_body={
            "player_name": player_name, "npc_name": npc_name, "area": area,
            "action": "leaving", "message": "Avatar leaving", "status": "end",
        },
    )


@mcp.tool()
def create_player_session(player_id: str) -> dict:
    """Create or initialize a player session, returning its initial state."""
    return _call("POST", f"/api/player/{player_id}/session")


@mcp.tool()
def close_player_session(player_id: str) -> dict:
    """Close a player session."""
    return _call("DELETE", f"/api/player/{player_id}/session")


@mcp.tool()
def process_player_input(player_id: str, player_input: str) -> dict:
    """Send a raw player command/input (e.g. '/go village', '/who', '/inventory') and
    get the game's response."""
    return _call("POST", f"/api/player/{player_id}/input", json_body={"input": player_input})


@mcp.tool()
def get_player_state(player_id: str) -> dict:
    """Get a player's current game state."""
    return _call("GET", f"/api/player/{player_id}/state")


@mcp.tool()
def get_player_profile(player_id: str) -> dict:
    """Get a player's psychological profile (LLM-derived from their conversations)."""
    return _call("GET", f"/api/player/{player_id}/profile")


@mcp.tool()
def get_player_inventory(player_id: str) -> dict:
    """Get a player's inventory and credits."""
    return _call("GET", f"/api/player/{player_id}/inventory")


@mcp.tool()
def get_conversation_history(player_id: str) -> dict:
    """Get a player's full conversation history across all NPCs."""
    return _call("GET", f"/api/player/{player_id}/conversation")


@mcp.tool()
def reset_conversation_history(player_id: str) -> dict:
    """DESTRUCTIVE: clear ALL conversation history for a player. No undo."""
    return _call("DELETE", f"/api/player/{player_id}/conversation/reset")


@mcp.tool()
def summarize_npc_conversation(player_id: str, npc_code: str) -> dict:
    """Generate a short LLM summary of one NPC's conversation with this player.
    npc_code is the 'area.npcname' form, lowercase (e.g. 'tavern.jorin')."""
    return _call("POST", f"/api/player/{player_id}/conversation/{npc_code}/summary")


@mcp.tool()
def reset_npc_conversation(player_id: str, npc_code: str) -> dict:
    """DESTRUCTIVE: clear conversation history with a single NPC. No undo."""
    return _call("DELETE", f"/api/player/{player_id}/conversation/{npc_code}")


@mcp.tool()
def get_player_storage_info(player_id: str) -> dict:
    """Get storage/usage info for a player (data size, NPCs talked to, etc)."""
    return _call("GET", f"/api/player/{player_id}/storage-info")


@mcp.tool()
def analyze_conversations(player_id: str) -> dict:
    """Generate a full LLM character-study analysis across all of a player's
    conversations (character development, relationship dynamics, personality)."""
    return _call("POST", f"/api/player/{player_id}/conversation/analyze")


@mcp.tool()
def get_conversation_analysis(player_id: str) -> dict:
    """Get a previously-generated conversation analysis for a player (404 if
    analyze_conversations hasn't been run for them yet)."""
    return _call("GET", f"/api/player/{player_id}/conversation/analysis")


@mcp.tool()
def process_game_command(player_name: str, command: str) -> dict:
    """Process a raw game command for a player, keyed by name rather than player_id
    (same underlying effect as process_player_input)."""
    return _call("POST", "/api/game/command", json_body={"player_name": player_name, "command": command})


@mcp.tool()
def list_commands() -> dict:
    """List the in-game slash commands available to players."""
    return _call("GET", "/api/commands")


@mcp.tool()
def reload_game_data() -> dict:
    """Reload NPC/story/area data from disk, without touching player data."""
    return _call("POST", "/api/admin/reload")


@mcp.tool()
def reset_database(key: str) -> dict:
    """EXTREMELY DESTRUCTIVE: delete ALL player data and reload NPC/story data from
    scratch. Requires the admin reset key (a separate secret from the Bearer token,
    checked by the endpoint itself) - never guess it, ask the operator."""
    return _call("POST", "/reset", json_body={"key": key})


@mcp.tool()
def call_endpoint(
    method: str, path: str,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict:
    """Generic passthrough to any Nexus REST endpoint not wrapped as its own tool above
    - call get_version or GET /api (via this tool) to see the full endpoint catalog.
    method is GET/POST/DELETE; path starts with '/', e.g. '/api/game/areas'."""
    return _call(method.upper(), path, json_body=json_body, params=params)


class BearerAuthMiddleware:
    """Rejects any request to the /mcp mount lacking the expected bearer token, so an
    MCP client needs the same credential app.py's REST endpoints require - the MCP
    surface gets no lighter protection than the plain HTTP API it wraps."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._expected = f"Bearer {token}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        if auth != self._expected:
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def build_asgi_app(flask_app) -> Starlette:
    """Combine the existing Flask REST API and this MCP server into one ASGI app on
    one port. Mounted routes don't get the parent's lifespan for free in Starlette,
    so the MCP session manager's lifespan (normally run by its own standalone
    Starlette app) is re-entered explicitly here - dropping this silently breaks
    every MCP session (the manager never starts, tool calls hang or 500)."""
    from asgiref.wsgi import WsgiToAsgi

    # streamable_http_path="/" because the whole sub-app is itself mounted at
    # "/mcp" below - its one internal route ends up serving exactly that path,
    # not "/mcp/mcp".
    mcp_app = mcp.streamable_http_app(streamable_http_path="/")
    protected_mcp_app = BearerAuthMiddleware(mcp_app, NEXUS_AUTH_TOKEN)
    flask_asgi = WsgiToAsgi(flask_app)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    async def redirect_to_mcp_slash(request: Request) -> RedirectResponse:
        # Mount("/mcp", ...) below only matches "/mcp/..." (a trailing slash is
        # baked into its compiled route regex) - without this, a client asking
        # for the bare "/mcp" (the natural way to write an MCP server URL) falls
        # through to the catch-all Flask mount and gets a Flask 404 instead, since
        # that mount matches every path as a prefix and is tried after this one
        # only by list order, never by specificity. 307 preserves the POST body.
        return RedirectResponse(url="/mcp/", status_code=307)

    return Starlette(
        routes=[
            Route("/mcp", redirect_to_mcp_slash, methods=["GET", "POST", "DELETE"]),
            Mount("/mcp", app=protected_mcp_app),
            Mount("/", app=flask_asgi),
        ],
        lifespan=lifespan,
    )
