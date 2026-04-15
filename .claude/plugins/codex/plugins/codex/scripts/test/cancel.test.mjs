import assert from "node:assert/strict";
import test from "node:test";

import { resolveCancelCleanupState } from "../lib/cancel.mjs";

const RUNNING_JOB = {
  id: "job-123",
  status: "running",
  phase: "running",
  pid: 4321
};
const PID_LESS_RUNNING_JOB = {
  ...RUNNING_JOB,
  pid: null
};

test("resolveCancelCleanupState marks jobs cancelled when cleanup is delivered", () => {
  const state = resolveCancelCleanupState(
    RUNNING_JOB,
    { attempted: true, delivered: true, method: "taskkill" },
    { completedAt: "2026-04-15T00:00:00.000Z" }
  );

  assert.equal(state.cancelled, true);
  assert.equal(state.status, "cancelled");
  assert.equal(state.phase, "cancelled");
  assert.equal(state.pid, null);
  assert.equal(state.completedAt, "2026-04-15T00:00:00.000Z");
  assert.equal(state.cleanupDelivered, true);
  assert.equal(state.cleanupError, null);
});

test("resolveCancelCleanupState treats missing processes as cancelled", () => {
  const state = resolveCancelCleanupState(RUNNING_JOB, {
    attempted: true,
    delivered: false,
    method: "taskkill"
  });

  assert.equal(state.cancelled, true);
  assert.equal(state.status, "cancelled");
  assert.equal(state.cleanupDelivered, false);
  assert.equal(state.cleanupError, null);
});

test("resolveCancelCleanupState treats successful turn interrupts without local pids as cancelled", () => {
  const state = resolveCancelCleanupState(
    PID_LESS_RUNNING_JOB,
    { attempted: false, delivered: false, method: null },
    {
      completedAt: "2026-04-15T00:00:00.000Z",
      turnInterruptSucceeded: true
    }
  );

  assert.equal(state.cancelled, true);
  assert.equal(state.status, "cancelled");
  assert.equal(state.phase, "cancelled");
  assert.equal(state.pid, null);
  assert.equal(state.completedAt, "2026-04-15T00:00:00.000Z");
  assert.equal(state.cleanupAttempted, false);
  assert.equal(state.cleanupDelivered, false);
  assert.equal(state.cleanupError, null);
});

test("resolveCancelCleanupState keeps pid-less jobs active when turn interrupt does not succeed", () => {
  const state = resolveCancelCleanupState(PID_LESS_RUNNING_JOB, {
    attempted: false,
    delivered: false,
    method: null
  });

  assert.equal(state.cancelled, false);
  assert.equal(state.status, "running");
  assert.equal(state.phase, "cancel failed");
  assert.equal(state.pid, null);
  assert.equal(state.cleanupAttempted, false);
  assert.equal(state.cleanupDelivered, false);
  assert.equal(state.cleanupError, "Could not confirm local process termination.");
});

test("resolveCancelCleanupState keeps the job active when cleanup fails", () => {
  const state = resolveCancelCleanupState(RUNNING_JOB, null, {
    cleanupError: new Error("Access is denied.")
  });

  assert.equal(state.cancelled, false);
  assert.equal(state.status, "running");
  assert.equal(state.phase, "cancel failed");
  assert.equal(state.pid, RUNNING_JOB.pid);
  assert.equal(state.completedAt, null);
  assert.equal(state.cleanupError, "Access is denied.");
});

test("resolveCancelCleanupState does not mask local cleanup errors when turn interrupt succeeds", () => {
  const state = resolveCancelCleanupState(RUNNING_JOB, null, {
    cleanupError: new Error("Access is denied."),
    turnInterruptSucceeded: true
  });

  assert.equal(state.cancelled, false);
  assert.equal(state.status, "running");
  assert.equal(state.phase, "cancel failed");
  assert.equal(state.pid, RUNNING_JOB.pid);
  assert.equal(state.completedAt, null);
  assert.equal(state.cleanupError, "Access is denied.");
});
