"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function writePairingArtifacts({ payload, payloadPath, qrPath, qrTextPath, repoRoot }) {
  const payloadJson = JSON.stringify(payload);
  fs.mkdirSync(path.dirname(payloadPath), { recursive: true });
  fs.writeFileSync(payloadPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");

  const result = spawnSync("python3", [path.join(repoRoot, "scripts", "cra_generate_qr_from_text.py"), payloadJson, qrPath], {
    encoding: "utf8",
  });
  if (result.status !== 0) {
    const message = (result.stderr || result.stdout || "Unknown QR generation failure").trim();
    throw new Error(`Failed to generate Remodex pairing QR: ${message}`);
  }

  const textStub = [
    "Remodex Pairing Payload",
    "",
    payloadJson,
    "",
    JSON.stringify(payload, null, 2),
  ].join("\n");
  fs.writeFileSync(qrTextPath, `${textStub}\n`, "utf8");

  return {
    payloadPath,
    qrPath,
    qrTextPath,
  };
}

module.exports = { writePairingArtifacts };
