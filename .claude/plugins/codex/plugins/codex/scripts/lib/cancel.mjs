function normalizeCleanupError(error) {
  if (error == null) {
    return null;
  }
  return error instanceof Error ? error.message : String(error);
}

function getActiveJobStatus(status) {
  return status === "queued" ? "queued" : "running";
}

export function resolveCancelCleanupState(job, cleanupResult, options = {}) {
  const cleanupAttempted = Boolean(cleanupResult?.attempted);
  const cleanupDelivered = Boolean(cleanupResult?.delivered);
  const cleanupError = normalizeCleanupError(options.cleanupError);
  const turnInterruptSucceeded = options.turnInterruptSucceeded === true;
  const hasUsablePid = Number.isFinite(job?.pid);
  const confirmedByLocalCleanup =
    !cleanupError &&
    (cleanupDelivered || (cleanupAttempted && cleanupResult?.delivered === false));
  const confirmedByTurnInterrupt = !cleanupError && turnInterruptSucceeded && !hasUsablePid;
  const confirmedStopped = confirmedByLocalCleanup || confirmedByTurnInterrupt;

  if (confirmedStopped) {
    return {
      cancelled: true,
      status: "cancelled",
      phase: "cancelled",
      pid: null,
      completedAt: options.completedAt ?? null,
      errorMessage: "Cancelled by user.",
      cleanupAttempted,
      cleanupDelivered,
      cleanupError: null
    };
  }

  return {
    cancelled: false,
    status: getActiveJobStatus(job?.status),
    phase: options.failedPhase ?? "cancel failed",
    pid: job?.pid ?? null,
    completedAt: null,
    errorMessage: null,
    cleanupAttempted,
    cleanupDelivered,
    cleanupError: cleanupError ?? "Could not confirm local process termination."
  };
}
