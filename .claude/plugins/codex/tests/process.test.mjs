import test from "node:test";
import assert from "node:assert/strict";

import process from "node:process";

import { runCommand, terminateProcessTree } from "../plugins/codex/scripts/lib/process.mjs";

test("runCommand passes shell metacharacters through as literal args", () => {
  const dangerous = "literal & echo INJECTED ; $(echo bad)";
  const result = runCommand(process.execPath, [
    "-e",
    "process.stdout.write(process.argv.slice(1).join('\\n'))",
    dangerous
  ]);

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), dangerous);
  assert.equal(result.stderr, "");
});

test("terminateProcessTree uses taskkill on Windows", () => {
  let captured = null;
  const outcome = terminateProcessTree(1234, {
    platform: "win32",
    runCommandImpl(command, args) {
      captured = { command, args };
      return {
        command,
        args,
        status: 0,
        signal: null,
        stdout: "",
        stderr: "",
        error: null
      };
    },
    killImpl() {
      throw new Error("kill fallback should not run");
    }
  });

  assert.deepEqual(captured, {
    command: "taskkill",
    args: ["/PID", "1234", "/T", "/F"]
  });
  assert.equal(outcome.delivered, true);
  assert.equal(outcome.method, "taskkill");
});

test("terminateProcessTree treats missing Windows processes as already stopped", () => {
  const outcome = terminateProcessTree(1234, {
    platform: "win32",
    runCommandImpl(command, args) {
      return {
        command,
        args,
        status: 128,
        signal: null,
        stdout: "ERROR: The process \"1234\" not found.",
        stderr: "",
        error: null
      };
    }
  });

  assert.equal(outcome.attempted, true);
  assert.equal(outcome.method, "taskkill");
  assert.equal(outcome.result.status, 128);
  assert.match(outcome.result.stdout, /not found/i);
});
