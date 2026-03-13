"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const test = require("node:test");
const assert = require("node:assert/strict");
const { loadOrCreateBridgeDeviceState } = require("../../remodex/device-state.js");
const { createBridgeSecureTransport, PAIRING_QR_VERSION } = require("../../remodex/secure-transport.js");

test("Remodex pairing payload matches expected scan schema", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "remodex-state-"));
  const statePath = path.join(tempDir, "device-state.json");
  const state = loadOrCreateBridgeDeviceState(statePath);
  const transport = createBridgeSecureTransport({
    sessionId: "session-1",
    relayUrl: "ws://relay.test:8787",
    deviceState: state,
    storePath: statePath,
  });

  const payload = transport.createPairingPayload();

  assert.equal(payload.v, PAIRING_QR_VERSION);
  assert.equal(payload.relay, "ws://relay.test:8787");
  assert.equal(payload.sessionId, "session-1");
  assert.equal(payload.macDeviceId, state.macDeviceId);
  assert.equal(payload.macIdentityPublicKey, state.macIdentityPublicKey);
  assert.equal(typeof payload.expiresAt, "number");
});

