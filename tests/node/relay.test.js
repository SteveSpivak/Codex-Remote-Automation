"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { parseSessionRequest } = require("../../relay/server.js");

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
  const parsed = parseSessionRequest(request("/abc123", { "x-role": "mac" }));
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

