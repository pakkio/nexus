#!/usr/bin/env node

/**
 * Generic MCP stdio-to-HTTP/WebSocket bridge.
 * Bridges stdio JSON-RPC (used by Claude Code / other MCP clients) to any
 * MCP server exposed over HTTP or WebSocket. This is nexus's own standalone
 * copy so this repo doesn't depend on craftsim being checked out too - it's
 * identical to /root/craftsim/scripts/mcp-craftsim-bridge.js (which serves
 * the same role for the mcp-craftsim server); keep them in sync if either
 * needs a real fix.
 *
 * Talks to the MCP server mounted at /mcp in this repo's own app.py (see
 * mcp_server.py), which deliberately answers with the same stateless
 * single-request/response HTTP contract mcp-craftsim uses
 * (stateless_http=True, json_response=True) - no SSE, no session-id
 * continuity - which is exactly what this bridge's plain POST-and-print
 * loop assumes.
 */

const readline = require("readline");

const rawUrl = process.env.MCP_URL || "http://127.0.0.1:5000/mcp/";
const token = process.env.MCP_TOKEN || "pakkio 62";

const headers = {
  "Content-Type": "application/json",
  "Authorization": `Bearer ${token}`
};

const isHttp = rawUrl.startsWith("http://") || rawUrl.startsWith("https://");

let ws;
let isConnected = isHttp;
const queue = [];

if (!isHttp) {
  try {
    ws = new WebSocket(rawUrl, { headers: { "Authorization": `Bearer ${token}` } });
  } catch (err) {
    console.error(`[mcp-bridge] WebSocket creation error: ${err.message}`);
    process.exit(1);
  }

  ws.addEventListener("open", () => {
    isConnected = true;
    while (queue.length > 0) {
      const msg = queue.shift();
      ws.send(msg);
    }
  });

  ws.addEventListener("message", (event) => {
    const data = typeof event.data === "string" ? event.data : event.data.toString();
    process.stdout.write(data + "\n");
  });

  ws.addEventListener("error", (err) => {
    console.error(`[mcp-bridge] WebSocket error: ${err.message || err}`);
  });

  ws.addEventListener("close", (event) => {
    isConnected = false;
    console.error(`[mcp-bridge] WebSocket closed (code: ${event.code}, reason: ${event.reason})`);
  });
}

async function sendHttp(line) {
  try {
    const res = await fetch(rawUrl, {
      method: "POST",
      headers,
      body: line
    });
    if (res.status === 200) {
      const data = await res.text();
      if (data && data.trim()) {
        process.stdout.write(data.trim() + "\n");
      }
    } else if (res.status !== 204 && res.status !== 202) {
      console.error(`[mcp-bridge] HTTP error ${res.status}: ${await res.text()}`);
    }
  } catch (err) {
    console.error(`[mcp-bridge] HTTP request failed: ${err.message}`);
  }
}

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on("line", (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  if (isHttp) {
    sendHttp(trimmed);
  } else {
    if (isConnected && ws.readyState === WebSocket.OPEN) {
      ws.send(trimmed);
    } else {
      queue.push(trimmed);
    }
  }
});

rl.on("close", () => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  process.exit(0);
});

process.on("SIGINT", () => {
  if (ws) ws.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  if (ws) ws.close();
  process.exit(0);
});
