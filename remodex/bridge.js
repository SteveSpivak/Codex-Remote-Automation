"use strict";

const fs = require("fs");
const path = require("path");
const { randomUUID } = require("crypto");
const { createCodexTransport } = require("./codex-transport");
const { defaultStorePath, loadOrCreateBridgeDeviceState } = require("./device-state");
const { writePairingArtifacts } = require("./qr");
const { createBridgeSecureTransport } = require("./secure-transport");

function repoRoot() {
  return path.resolve(__dirname, "..");
}

function defaultRuntimeDir() {
  return path.join(repoRoot(), "var", "remodex-bridge");
}

function parseArgs(argv) {
  const parsed = {
    relayUrl: "ws://127.0.0.1:8787",
    runtimeDir: defaultRuntimeDir(),
    cwd: repoRoot(),
    pairOnly: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--relay-url" && next) {
      parsed.relayUrl = next;
      index += 1;
      continue;
    }
    if (arg === "--runtime-dir" && next) {
      parsed.runtimeDir = path.resolve(next);
      index += 1;
      continue;
    }
    if (arg === "--cwd" && next) {
      parsed.cwd = path.resolve(next);
      index += 1;
      continue;
    }
    if (arg === "--pair-only") {
      parsed.pairOnly = true;
      continue;
    }
  }

  return parsed;
}

function runtimePaths(runtimeDir) {
  return {
    runtimeDir,
    deviceStatePath: path.join(runtimeDir, "device-state.json"),
    statePath: path.join(runtimeDir, "bridge-state.json"),
    payloadPath: path.join(runtimeDir, "pairing-payload.json"),
    qrPath: path.join(runtimeDir, "pairing-qr.png"),
    qrTextPath: path.join(runtimeDir, "pairing-qr.txt"),
  };
}

function writeJson(pathname, payload) {
  fs.mkdirSync(path.dirname(pathname), { recursive: true });
  fs.writeFileSync(pathname, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function startBridge() {
  const args = parseArgs(process.argv.slice(2));
  const paths = runtimePaths(args.runtimeDir);
  const deviceStatePath = paths.deviceStatePath || defaultStorePath(repoRoot());
  const deviceState = loadOrCreateBridgeDeviceState(deviceStatePath);
  const sessionId = randomUUID();
  const relayBaseUrl = args.relayUrl.replace(/\/+$/, "");
  const relaySessionUrl = `${relayBaseUrl}/${sessionId}?role=mac`;

  const secureTransport = createBridgeSecureTransport({
    sessionId,
    relayUrl: relayBaseUrl,
    deviceState,
    storePath: deviceStatePath,
  });
  const pairingPayload = secureTransport.createPairingPayload();
  writePairingArtifacts({
    payload: pairingPayload,
    payloadPath: paths.payloadPath,
    qrPath: paths.qrPath,
    qrTextPath: paths.qrTextPath,
    repoRoot: repoRoot(),
  });

  const state = {
    status: "starting",
    sessionId,
    relayUrl: relayBaseUrl,
    relaySessionUrl,
    secureReady: false,
    payloadPath: paths.payloadPath,
    qrPath: paths.qrPath,
    qrTextPath: paths.qrTextPath,
    updatedAt: new Date().toISOString(),
  };
  writeJson(paths.statePath, state);

  if (args.pairOnly) {
    state.status = "pair_only";
    state.updatedAt = new Date().toISOString();
    writeJson(paths.statePath, state);
    process.stdout.write(`${JSON.stringify(state, null, 2)}\n`);
    return;
  }

  let socket = null;
  let reconnectAttempt = 0;
  let reconnectTimer = null;
  let codexHandshakeState = "cold";
  const forwardedInitializeRequestIds = new Set();

  const codex = createCodexTransport({ cwd: args.cwd });
  codex.onError((error) => {
    state.status = "error";
    state.lastError = String(error.message || error);
    state.updatedAt = new Date().toISOString();
    writeJson(paths.statePath, state);
    console.error(error.message);
    process.exit(1);
  });
  codex.onClose(() => {
    state.status = "closed";
    state.updatedAt = new Date().toISOString();
    writeJson(paths.statePath, state);
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
  });
  codex.onMessage((message) => {
    trackCodexHandshakeState(message);
    secureTransport.queueOutboundApplicationMessage(message, (wireMessage) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(wireMessage);
      }
    });
  });

  function connectRelay() {
    clearReconnectTimer();
    socket = new WebSocket(relaySessionUrl);

    socket.addEventListener("open", () => {
      reconnectAttempt = 0;
      state.status = "connected";
      state.updatedAt = new Date().toISOString();
      writeJson(paths.statePath, state);
      secureTransport.bindLiveSendWireMessage((wireMessage) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(wireMessage);
        }
      });
    });

    socket.addEventListener("message", (event) => {
      const rawMessage = typeof event.data === "string" ? event.data : Buffer.from(event.data).toString("utf8");
      if (secureTransport.handleIncomingWireMessage(rawMessage, {
        sendControlMessage(controlMessage) {
          if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(controlMessage));
          }
        },
        onApplicationMessage(plaintextMessage) {
          handleApplicationMessage(plaintextMessage);
        },
      })) {
        state.secureReady = secureTransport.isSecureChannelReady();
        state.updatedAt = new Date().toISOString();
        writeJson(paths.statePath, state);
      }
    });

    socket.addEventListener("close", () => {
      state.status = "disconnected";
      state.secureReady = false;
      state.updatedAt = new Date().toISOString();
      writeJson(paths.statePath, state);
      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      // close handler manages retries and state.
    });
  }

  function handleApplicationMessage(rawMessage) {
    if (handleBridgeManagedHandshakeMessage(rawMessage)) {
      return;
    }
    codex.send(rawMessage);
  }

  function sendApplicationResponse(rawMessage) {
    secureTransport.queueOutboundApplicationMessage(rawMessage, (wireMessage) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(wireMessage);
      }
    });
  }

  function handleBridgeManagedHandshakeMessage(rawMessage) {
    let parsed = null;
    try {
      parsed = JSON.parse(rawMessage);
    } catch {
      return false;
    }

    const method = typeof parsed?.method === "string" ? parsed.method.trim() : "";
    if (!method) {
      return false;
    }

    if (method === "initialize" && parsed.id != null) {
      if (codexHandshakeState !== "warm") {
        forwardedInitializeRequestIds.add(String(parsed.id));
        return false;
      }

      sendApplicationResponse(JSON.stringify({
        id: parsed.id,
        result: {
          bridgeManaged: true,
        },
      }));
      return true;
    }

    if (method === "initialized") {
      return codexHandshakeState === "warm";
    }

    return false;
  }

  function trackCodexHandshakeState(rawMessage) {
    let parsed = null;
    try {
      parsed = JSON.parse(rawMessage);
    } catch {
      return;
    }

    const responseId = parsed?.id;
    if (responseId == null) {
      return;
    }

    const responseKey = String(responseId);
    if (!forwardedInitializeRequestIds.has(responseKey)) {
      return;
    }

    forwardedInitializeRequestIds.delete(responseKey);
    if (parsed?.result != null) {
      codexHandshakeState = "warm";
      return;
    }

    const errorMessage = typeof parsed?.error?.message === "string" ? parsed.error.message.toLowerCase() : "";
    if (errorMessage.includes("already initialized")) {
      codexHandshakeState = "warm";
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) {
      return;
    }
    reconnectAttempt += 1;
    const delayMs = Math.min(1000 * reconnectAttempt, 5000);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectRelay();
    }, delayMs);
  }

  function clearReconnectTimer() {
    if (!reconnectTimer) {
      return;
    }
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  connectRelay();
  process.stdout.write(`${JSON.stringify(state, null, 2)}\n`);

  process.on("SIGINT", () => shutdown());
  process.on("SIGTERM", () => shutdown());

  function shutdown() {
    clearReconnectTimer();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    codex.shutdown();
    process.exit(0);
  }
}

if (require.main === module) {
  startBridge();
}

module.exports = { startBridge };
