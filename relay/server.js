"use strict";

const http = require("http");
const { URL } = require("url");
const { WebSocketServer, WebSocket } = require("ws");

const HOST = process.env.CRA_RELAY_HOST || "127.0.0.1";
const PORT = Number(process.env.CRA_RELAY_PORT || 8787);
const HEARTBEAT_INTERVAL_MS = Number(process.env.CRA_RELAY_HEARTBEAT_MS || 15000);
const SESSION_TTL_MS = Number(process.env.CRA_RELAY_SESSION_TTL_MS || 60000);
const VALID_ROLES = new Set(["mac", "iphone", "phone"]);

function createSessionState(sessionId) {
  return {
    sessionId,
    sockets: new Set(),
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

function normalizeRole(rawRole) {
  const role = String(rawRole || "").trim().toLowerCase();
  if (!VALID_ROLES.has(role)) {
    return "";
  }
  return role === "phone" ? "iphone" : role;
}

function logRelayEvent(event, fields = {}) {
  console.log(
    JSON.stringify({
      component: "cra-relay",
      timestamp: new Date().toISOString(),
      event,
      ...fields,
    })
  );
}

function touchSession(session) {
  session.updatedAt = Date.now();
}

function getSession(sessions, sessionId) {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, createSessionState(sessionId));
  }
  return sessions.get(sessionId);
}

function summarizeSessions(sessions) {
  let sockets = 0;
  for (const session of sessions.values()) {
    sockets += session.sockets.size;
  }
  return {
    sessions: sessions.size,
    sockets,
  };
}

function removeSocket(sessions, sessionId, socket, reason = "close") {
  const session = sessions.get(sessionId);
  if (!session) {
    return;
  }
  const removed = session.sockets.delete(socket);
  if (removed) {
    touchSession(session);
    logRelayEvent("peer_removed", {
      sessionId,
      role: socket.role || "unknown",
      reason,
      peersRemaining: session.sockets.size,
    });
  }
  if (session.sockets.size === 0) {
    sessions.delete(sessionId);
    logRelayEvent("session_deleted", { sessionId, reason });
  }
}

function handleTextMessage(sessions, socket, message) {
  const session = sessions.get(socket.sessionId);
  if (!session) {
    return;
  }
  touchSession(session);
  let delivered = 0;
  for (const peer of session.sockets) {
    if (peer === socket) {
      continue;
    }
    if (peer.readyState !== WebSocket.OPEN) {
      continue;
    }
    peer.send(message, { binary: false }, (error) => {
      if (error) {
        logRelayEvent("send_error", {
          sessionId: socket.sessionId,
          role: peer.role || "unknown",
          message: String(error.message || error),
        });
      }
    });
    delivered += 1;
  }
  logRelayEvent("message_routed", {
    sessionId: socket.sessionId,
    sourceRole: socket.role || "unknown",
    delivered,
    bytes: Buffer.byteLength(message, "utf8"),
  });
}

function parseSessionRequest(request) {
  const requestUrl = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  const segments = requestUrl.pathname.split("/").filter(Boolean);

  let sessionId = "";
  if (segments.length === 2 && segments[0] === "relay") {
    sessionId = segments[1];
  } else if (segments.length === 2 && segments[0] === "session") {
    sessionId = segments[1];
  } else if (segments.length === 1) {
    sessionId = segments[0];
  }

  const role = normalizeRole(
    request.headers["x-role"] || requestUrl.searchParams.get("role") || ""
  );

  if (!sessionId || !role) {
    return null;
  }

  return { sessionId, role };
}

function createRelayServer(options = {}) {
  const host = options.host || HOST;
  const port = Number(options.port || PORT);
  const heartbeatIntervalMs = Number(options.heartbeatIntervalMs || HEARTBEAT_INTERVAL_MS);
  const sessionTtlMs = Number(options.sessionTtlMs || SESSION_TTL_MS);
  const sessions = new Map();
  const wss = new WebSocketServer({
    noServer: true,
    clientTracking: false,
    perMessageDeflate: false,
  });

  const server = http.createServer((request, response) => {
    const requestUrl = new URL(request.url, `http://${request.headers.host || "localhost"}`);
    if (requestUrl.pathname === "/health") {
      const summary = summarizeSessions(sessions);
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({ status: "ok", host, port, ...summary }));
      return;
    }
    response.writeHead(404, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: "not_found" }));
  });

  wss.on("connection", (socket, request, sessionRequest) => {
    const session = getSession(sessions, sessionRequest.sessionId);
    socket.isAlive = true;
    socket.sessionId = sessionRequest.sessionId;
    socket.role = sessionRequest.role;
    session.sockets.add(socket);
    touchSession(session);

    logRelayEvent("peer_connected", {
      sessionId: socket.sessionId,
      role: socket.role,
      peersInSession: session.sockets.size,
      remoteAddress: request.socket.remoteAddress || "",
    });

    socket.on("pong", () => {
      socket.isAlive = true;
      touchSession(session);
    });

    socket.on("message", (payload, isBinary) => {
      if (isBinary) {
        return;
      }
      handleTextMessage(sessions, socket, payload.toString("utf8"));
    });

    socket.on("close", (code) => {
      removeSocket(sessions, socket.sessionId, socket, `close:${code}`);
    });

    socket.on("error", (error) => {
      logRelayEvent("peer_error", {
        sessionId: socket.sessionId,
        role: socket.role || "unknown",
        message: String(error.message || error),
      });
      removeSocket(sessions, socket.sessionId, socket, "error");
    });
  });

  server.on("upgrade", (request, socket, head) => {
    const sessionRequest = parseSessionRequest(request);
    if (!sessionRequest) {
      socket.write("HTTP/1.1 404 Not Found\r\n\r\n");
      socket.destroy();
      return;
    }

    wss.handleUpgrade(request, socket, head, (ws) => {
      wss.emit("connection", ws, request, sessionRequest);
    });
  });

  const heartbeat = setInterval(() => {
    const now = Date.now();
    for (const [sessionId, session] of sessions.entries()) {
      for (const socket of Array.from(session.sockets)) {
        if (socket.readyState === WebSocket.CLOSING || socket.readyState === WebSocket.CLOSED) {
          removeSocket(sessions, sessionId, socket, "closed");
          continue;
        }
        if (socket.readyState !== WebSocket.OPEN) {
          continue;
        }
        if (socket.isAlive === false) {
          logRelayEvent("peer_terminated", {
            sessionId,
            role: socket.role || "unknown",
            reason: "heartbeat-timeout",
          });
          socket.terminate();
          removeSocket(sessions, sessionId, socket, "heartbeat-timeout");
          continue;
        }
        socket.isAlive = false;
        socket.ping();
      }

      if (session.sockets.size === 0 && now - session.updatedAt >= sessionTtlMs) {
        sessions.delete(sessionId);
        logRelayEvent("session_expired", { sessionId, idleMs: now - session.updatedAt });
      }
    }
  }, heartbeatIntervalMs);
  if (typeof heartbeat.unref === "function") {
    heartbeat.unref();
  }

  server.on("close", () => {
    clearInterval(heartbeat);
    for (const session of sessions.values()) {
      for (const socket of session.sockets) {
        socket.terminate();
      }
    }
    sessions.clear();
    wss.close();
  });

  server.relayState = {
    sessions,
    heartbeatIntervalMs,
    sessionTtlMs,
  };

  return server;
}

const server = createRelayServer();

if (require.main === module) {
  server.listen(PORT, HOST, () => {
    logRelayEvent("listening", {
      url: `ws://${HOST}:${PORT}`,
      canonicalPath: "/relay/<session_id>",
      legacyPaths: ["/<session_id>", "/session/<session_id>?role=<role>"],
    });
  });
}

module.exports = {
  createRelayServer,
  parseSessionRequest,
  normalizeRole,
};
