"use strict";

const { spawn } = require("child_process");

function createCodexTransport({ cwd, env = process.env } = {}) {
  const codex = spawn("codex", ["app-server"], {
    cwd,
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...env },
  });

  let stdoutBuffer = "";
  let stderrBuffer = "";
  let didRequestShutdown = false;
  let didReportError = false;
  const listeners = createListenerBag();

  codex.on("error", (error) => {
    didReportError = true;
    listeners.emitError(error);
  });

  codex.on("close", (code, signal) => {
    if (!didRequestShutdown && !didReportError && code !== 0) {
      didReportError = true;
      listeners.emitError(createCodexCloseError({ code, signal, stderrBuffer }));
      return;
    }
    listeners.emitClose(code, signal);
  });

  codex.stderr.on("data", (chunk) => {
    stderrBuffer = appendOutputBuffer(stderrBuffer, chunk.toString("utf8"));
  });

  codex.stdout.on("data", (chunk) => {
    stdoutBuffer += chunk.toString("utf8");
    const lines = stdoutBuffer.split("\n");
    stdoutBuffer = lines.pop() || "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed) {
        listeners.emitMessage(trimmed);
      }
    }
  });

  return {
    send(message) {
      if (!codex.stdin.writable) {
        return;
      }
      codex.stdin.write(message.endsWith("\n") ? message : `${message}\n`);
    },
    onMessage(handler) {
      listeners.onMessage = handler;
    },
    onClose(handler) {
      listeners.onClose = handler;
    },
    onError(handler) {
      listeners.onError = handler;
    },
    shutdown() {
      didRequestShutdown = true;
      if (!codex.killed && codex.exitCode === null) {
        codex.kill("SIGTERM");
      }
    },
  };
}

function createCodexCloseError({ code, signal, stderrBuffer }) {
  const details = stderrBuffer.trim();
  const reason = details || `Process exited with code ${code}${signal ? ` (signal: ${signal})` : ""}.`;
  return new Error(`Codex app-server failed: ${reason}`);
}

function appendOutputBuffer(buffer, chunk) {
  const next = `${buffer}${chunk}`;
  return next.slice(-4096);
}

function createListenerBag() {
  return {
    onMessage: null,
    onClose: null,
    onError: null,
    emitMessage(message) {
      this.onMessage?.(message);
    },
    emitClose(...args) {
      this.onClose?.(...args);
    },
    emitError(error) {
      this.onError?.(error);
    },
  };
}

module.exports = { createCodexTransport };

