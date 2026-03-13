"use strict";

const crypto = require("crypto");
const http = require("http");
const { URL } = require("url");

const HOST = process.env.CRA_RELAY_HOST || "0.0.0.0";
const PORT = Number(process.env.CRA_RELAY_PORT || 8787);
const sessions = new Map();

function createSessionState() {
  return {
    sockets: new Set(),
  };
}

function getSession(sessionId) {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, createSessionState());
  }
  return sessions.get(sessionId);
}

function removeSocket(sessionId, socket) {
  const session = sessions.get(sessionId);
  if (!session) {
    return;
  }
  session.sockets.delete(socket);
  if (session.sockets.size === 0) {
    sessions.delete(sessionId);
  }
}

function sendTextFrame(socket, text) {
  const payload = Buffer.from(text, "utf8");
  let header = Buffer.from([0x81, 0x00]);
  if (payload.length < 126) {
    header[1] = payload.length;
  } else if (payload.length < 65536) {
    header = Buffer.concat([
      Buffer.from([0x81, 126]),
      Buffer.from([(payload.length >> 8) & 0xff, payload.length & 0xff]),
    ]);
  } else {
    const extended = Buffer.alloc(8);
    extended.writeBigUInt64BE(BigInt(payload.length), 0);
    header = Buffer.concat([Buffer.from([0x81, 127]), extended]);
  }
  socket.write(Buffer.concat([header, payload]));
}

function parseFrames(socket, chunk) {
  socket.frameBuffer = Buffer.concat([socket.frameBuffer || Buffer.alloc(0), chunk]);
  while (socket.frameBuffer.length >= 2) {
    const first = socket.frameBuffer[0];
    const second = socket.frameBuffer[1];
    const opcode = first & 0x0f;
    const masked = Boolean(second & 0x80);
    let offset = 2;
    let length = second & 0x7f;

    if (length === 126) {
      if (socket.frameBuffer.length < offset + 2) {
        return;
      }
      length = socket.frameBuffer.readUInt16BE(offset);
      offset += 2;
    } else if (length === 127) {
      if (socket.frameBuffer.length < offset + 8) {
        return;
      }
      length = Number(socket.frameBuffer.readBigUInt64BE(offset));
      offset += 8;
    }

    const maskLength = masked ? 4 : 0;
    if (socket.frameBuffer.length < offset + maskLength + length) {
      return;
    }

    const mask = masked ? socket.frameBuffer.subarray(offset, offset + 4) : null;
    offset += maskLength;
    let payload = socket.frameBuffer.subarray(offset, offset + length);
    socket.frameBuffer = socket.frameBuffer.subarray(offset + length);

    if (mask) {
      const unmasked = Buffer.alloc(payload.length);
      for (let index = 0; index < payload.length; index += 1) {
        unmasked[index] = payload[index] ^ mask[index % 4];
      }
      payload = unmasked;
    }

    if (opcode === 0x8) {
      socket.end();
      return;
    }
    if (opcode === 0x9) {
      socket.write(Buffer.concat([Buffer.from([0x8a, payload.length]), payload]));
      continue;
    }
    if (opcode !== 0x1) {
      continue;
    }
    handleTextMessage(socket, payload.toString("utf8"));
  }
}

function handleTextMessage(socket, message) {
  const session = sessions.get(socket.sessionId);
  if (!session) {
    return;
  }
  for (const peer of session.sockets) {
    if (peer === socket) {
      continue;
    }
    if (peer.destroyed) {
      continue;
    }
    sendTextFrame(peer, message);
  }
}

function handleUpgrade(request, socket) {
  const requestUrl = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  const segments = requestUrl.pathname.split("/").filter(Boolean);
  if (segments.length !== 2 || segments[0] !== "session") {
    socket.write("HTTP/1.1 404 Not Found\r\n\r\n");
    socket.destroy();
    return;
  }

  const sessionId = segments[1];
  const role = requestUrl.searchParams.get("role");
  if (!sessionId || !role || !["mac", "iphone"].includes(role)) {
    socket.write("HTTP/1.1 400 Bad Request\r\n\r\n");
    socket.destroy();
    return;
  }

  const key = request.headers["sec-websocket-key"];
  if (!key) {
    socket.write("HTTP/1.1 400 Bad Request\r\n\r\n");
    socket.destroy();
    return;
  }

  const accept = crypto
    .createHash("sha1")
    .update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
    .digest("base64");

  socket.write(
    [
      "HTTP/1.1 101 Switching Protocols",
      "Upgrade: websocket",
      "Connection: Upgrade",
      `Sec-WebSocket-Accept: ${accept}`,
      "\r\n",
    ].join("\r\n")
  );

  socket.sessionId = sessionId;
  socket.role = role;
  socket.frameBuffer = Buffer.alloc(0);
  getSession(sessionId).sockets.add(socket);

  socket.on("data", (chunk) => parseFrames(socket, chunk));
  socket.on("close", () => removeSocket(sessionId, socket));
  socket.on("end", () => removeSocket(sessionId, socket));
  socket.on("error", () => removeSocket(sessionId, socket));
}

const server = http.createServer((request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host || "localhost"}`);
  if (requestUrl.pathname === "/health") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "ok", sessions: sessions.size }));
    return;
  }
  response.writeHead(404, { "content-type": "application/json" });
  response.end(JSON.stringify({ error: "not_found" }));
});

server.on("upgrade", handleUpgrade);

server.listen(PORT, HOST, () => {
  console.log(`[cra-relay] listening on ws://${HOST}:${PORT}`);
});
