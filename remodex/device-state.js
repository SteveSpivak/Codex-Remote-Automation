"use strict";

const fs = require("fs");
const path = require("path");
const { randomUUID, generateKeyPairSync } = require("crypto");

function defaultStorePath(repoRoot) {
  return path.join(repoRoot, "var", "remodex-bridge", "device-state.json");
}

function loadOrCreateBridgeDeviceState(storePath) {
  const existingState = readBridgeDeviceState(storePath);
  if (existingState) {
    return existingState;
  }

  const nextState = createBridgeDeviceState();
  writeBridgeDeviceState(storePath, nextState);
  return nextState;
}

function rememberTrustedPhone(storePath, state, phoneDeviceId, phoneIdentityPublicKey) {
  const normalizedDeviceId = normalizeNonEmptyString(phoneDeviceId);
  const normalizedPublicKey = normalizeNonEmptyString(phoneIdentityPublicKey);
  if (!normalizedDeviceId || !normalizedPublicKey) {
    return state;
  }

  const nextState = {
    ...state,
    trustedPhones: {
      [normalizedDeviceId]: normalizedPublicKey,
    },
  };
  writeBridgeDeviceState(storePath, nextState);
  return nextState;
}

function getTrustedPhonePublicKey(state, phoneDeviceId) {
  const normalizedDeviceId = normalizeNonEmptyString(phoneDeviceId);
  if (!normalizedDeviceId) {
    return null;
  }
  return state.trustedPhones?.[normalizedDeviceId] || null;
}

function createBridgeDeviceState() {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const privateJwk = privateKey.export({ format: "jwk" });
  const publicJwk = publicKey.export({ format: "jwk" });

  return {
    version: 1,
    macDeviceId: randomUUID(),
    macIdentityPublicKey: base64UrlToBase64(publicJwk.x),
    macIdentityPrivateKey: base64UrlToBase64(privateJwk.d),
    trustedPhones: {},
  };
}

function readBridgeDeviceState(storePath) {
  if (!fs.existsSync(storePath)) {
    return null;
  }

  try {
    const rawState = JSON.parse(fs.readFileSync(storePath, "utf8"));
    return normalizeBridgeDeviceState(rawState);
  } catch {
    return null;
  }
}

function writeBridgeDeviceState(storePath, state) {
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  fs.writeFileSync(storePath, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 });
  try {
    fs.chmodSync(storePath, 0o600);
  } catch {
    // Best effort only.
  }
}

function normalizeBridgeDeviceState(rawState) {
  const macDeviceId = normalizeNonEmptyString(rawState?.macDeviceId);
  const macIdentityPublicKey = normalizeNonEmptyString(rawState?.macIdentityPublicKey);
  const macIdentityPrivateKey = normalizeNonEmptyString(rawState?.macIdentityPrivateKey);

  if (!macDeviceId || !macIdentityPublicKey || !macIdentityPrivateKey) {
    throw new Error("Bridge device state is incomplete");
  }

  const trustedPhones = {};
  if (rawState?.trustedPhones && typeof rawState.trustedPhones === "object") {
    for (const [deviceId, publicKey] of Object.entries(rawState.trustedPhones)) {
      const normalizedDeviceId = normalizeNonEmptyString(deviceId);
      const normalizedPublicKey = normalizeNonEmptyString(publicKey);
      if (!normalizedDeviceId || !normalizedPublicKey) {
        continue;
      }
      trustedPhones[normalizedDeviceId] = normalizedPublicKey;
    }
  }

  return {
    version: 1,
    macDeviceId,
    macIdentityPublicKey,
    macIdentityPrivateKey,
    trustedPhones,
  };
}

function normalizeNonEmptyString(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim();
}

function base64UrlToBase64(value) {
  if (typeof value !== "string" || value.length === 0) {
    return "";
  }
  const padded = `${value}${"=".repeat((4 - (value.length % 4 || 4)) % 4)}`;
  return padded.replace(/-/g, "+").replace(/_/g, "/");
}

module.exports = {
  defaultStorePath,
  getTrustedPhonePublicKey,
  loadOrCreateBridgeDeviceState,
  rememberTrustedPhone,
};

