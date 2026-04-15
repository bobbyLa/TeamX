import test from "node:test";
import assert from "node:assert/strict";

import { splitRawArgumentString } from "../plugins/codex/scripts/lib/args.mjs";

test("splitRawArgumentString preserves literal Windows paths", () => {
  assert.deepEqual(splitRawArgumentString("--cwd C:\\Team2\\TeamX"), ["--cwd", "C:\\Team2\\TeamX"]);
  assert.deepEqual(splitRawArgumentString('fix "src\\api\\v1.ts"'), ["fix", "src\\api\\v1.ts"]);
});

test("splitRawArgumentString still supports quoted and escaped segments", () => {
  assert.deepEqual(splitRawArgumentString('say "hello world"'), ["say", "hello world"]);
  assert.deepEqual(splitRawArgumentString('say "hello \\"world\\""'), ["say", 'hello "world"']);
  assert.deepEqual(splitRawArgumentString("say escaped\\ value"), ["say", "escaped value"]);
});
