"use strict";

const http = require("node:http");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const { once } = require("node:events");
const { createRequire } = require("node:module");
const { createRelayServer, parseSessionRequest } = require("../../relay/server.js");

const relayRequire = createRequire(path.resolve(__dirname, "../../relay/package.json"));
const WebSocket = relayRequire("ws");

function request(url, headers = {}) {
  return {
    url,
    headers: {
      host: "relay.test:8787",
      ...headers,
    },
  };
}

test("relay accepts Remodex path with x-role header", () => {
  const parsed = parseSessionRequest(request("/relay/abc123", { "x-role": "mac" }));
  assert.deepEqual(parsed, { sessionId: "abc123", role: "mac" });
});

test("relay accepts legacy CRA session path with role query", () => {
  const parsed = parseSessionRequest(request("/session/abc123?role=iphone"));
  assert.deepEqual(parsed, { sessionId: "abc123", role: "iphone" });
});

test("relay normalizes phone role to iphone", () => {
  const parsed = parseSessionRequest(request("/abc123", { "x-role": "phone" }));
  assert.deepEqual(parsed, { sessionId: "abc123", role: "iphone" });
});

test("relay rejects invalid session request", () => {
  const parsed = parseSessionRequest(request("/invalid/path"));
  assert.equal(parsed, null);
});

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          resolve(JSON.parse(body));
        });
      })
      .on("error", reject);
  });
}

test("relay routes text frames between canonical peers and reports health", async (context) => {
  const server = createRelayServer({ heartbeatIntervalMs: 25, sessionTtlMs: 50 });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  context.after(() => new Promise((resolve) => server.close(resolve)));

  const { port } = server.address();
  const mac = new WebSocket(`ws://127.0.0.1:${port}/relay/session-1`, {
    headers: { "x-role": "mac" },
  });
  const phone = new WebSocket(`ws://127.0.0.1:${port}/relay/session-1`, {
    headers: { "x-role": "phone" },
  });

  context.after(() => {
    mac.terminate();
    phone.terminate();
  });

  await Promise.all([once(mac, "open"), once(phone, "open")]);

  const before = await fetchJson(`http://127.0.0.1:${port}/health`);
  assert.equal(before.sessions, 1);
  assert.equal(before.sockets, 2);

  const messagePromise = once(phone, "message");
  mac.send("hello-relay");
  const [message] = await messagePromise;
  assert.equal(message.toString("utf8"), "hello-relay");

  mac.close();
  phone.close();
  await Promise.all([once(mac, "close"), once(phone, "close")]);

  await new Promise((resolve) => setTimeout(resolve, 80));
  const after = await fetchJson(`http://127.0.0.1:${port}/health`);
  assert.equal(after.sessions, 0);
  assert.equal(after.sockets, 0);
});
