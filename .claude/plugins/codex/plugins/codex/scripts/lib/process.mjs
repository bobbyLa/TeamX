import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import process from "node:process";

const WINDOWS_EXECUTABLE_EXTENSIONS = new Set([".com", ".exe"]);
const WINDOWS_CMD_SCRIPT_EXTENSIONS = new Set([".bat", ".cmd"]);
const WINDOWS_POWERSHELL_SCRIPT_EXTENSIONS = new Set([".ps1"]);
const DEFAULT_WINDOWS_PATHEXT = [".com", ".exe", ".bat", ".cmd", ".ps1"];

function getWindowsPathEntries(env = process.env) {
  const rawPath = env.Path ?? env.PATH ?? "";
  return rawPath.split(";").map((value) => value.trim()).filter(Boolean);
}

function getWindowsPathExt(env = process.env) {
  const rawPathExt = env.PATHEXT ?? env.PathExt ?? "";
  const extensions = rawPathExt
    ? rawPathExt.split(";").map((value) => value.trim().toLowerCase()).filter(Boolean)
    : DEFAULT_WINDOWS_PATHEXT;

  return [...new Set(extensions)];
}

function resolveWindowsCommandPath(command, cwd, env = process.env) {
  const normalizedCwd = cwd ?? process.cwd();
  const hasPath = path.isAbsolute(command) || /[\\/]/.test(command);
  const extension = path.extname(command).toLowerCase();

  if (hasPath) {
    const basePath = path.isAbsolute(command) ? command : path.resolve(normalizedCwd, command);
    if (extension) {
      return fs.existsSync(basePath) ? basePath : null;
    }

    for (const candidateExtension of getWindowsPathExt(env)) {
      const candidatePath = `${basePath}${candidateExtension}`;
      if (fs.existsSync(candidatePath)) {
        return candidatePath;
      }
    }
    return null;
  }

  for (const directory of getWindowsPathEntries(env)) {
    if (extension) {
      const candidatePath = path.join(directory, command);
      if (fs.existsSync(candidatePath)) {
        return candidatePath;
      }
      continue;
    }

    for (const candidateExtension of getWindowsPathExt(env)) {
      const candidatePath = path.join(directory, `${command}${candidateExtension}`);
      if (fs.existsSync(candidatePath)) {
        return candidatePath;
      }
    }
  }

  return null;
}

function quoteCmdArgument(value) {
  const text = String(value);
  if (text === "") {
    return '""';
  }

  const escaped = text.replace(/"/g, '""').replace(/%/g, "%%");
  if (!/[\s"&<>^|()!]/.test(text) && escaped === text) {
    return escaped;
  }

  return `"${escaped}"`;
}

function quoteCmdCommandLine(commandLine) {
  return `"${commandLine}"`;
}

function buildWindowsSpawnSpec(command, args, options = {}) {
  const env = options.env ?? process.env;
  const resolvedPath = resolveWindowsCommandPath(command, options.cwd, env);
  const commandPath = resolvedPath ?? command;
  const extension = path.extname(commandPath).toLowerCase();

  if (WINDOWS_CMD_SCRIPT_EXTENSIONS.has(extension)) {
    const commandLine = [quoteCmdArgument(commandPath), ...args.map(quoteCmdArgument)].join(" ");
    return {
      command: env.ComSpec ?? process.env.ComSpec ?? "cmd.exe",
      args: ["/d", "/s", "/c", quoteCmdCommandLine(commandLine)],
      windowsVerbatimArguments: true
    };
  }

  if (WINDOWS_POWERSHELL_SCRIPT_EXTENSIONS.has(extension)) {
    return {
      command: "powershell.exe",
      args: ["-NoLogo", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", commandPath, ...args]
    };
  }

  if (resolvedPath && WINDOWS_EXECUTABLE_EXTENSIONS.has(extension)) {
    return {
      command: commandPath,
      args
    };
  }

  return {
    command: commandPath,
    args
  };
}

export function runCommand(command, args = [], options = {}) {
  const env = options.env ?? process.env;
  const spawnSpec =
    process.platform === "win32"
      ? buildWindowsSpawnSpec(command, args, {
          cwd: options.cwd,
          env
        })
      : { command, args };

  const result = spawnSync(spawnSpec.command, spawnSpec.args, {
    cwd: options.cwd,
    env,
    encoding: "utf8",
    input: options.input,
    maxBuffer: options.maxBuffer,
    stdio: options.stdio ?? "pipe",
    shell: false,
    windowsHide: true,
    windowsVerbatimArguments: Boolean(spawnSpec.windowsVerbatimArguments)
  });

  return {
    command,
    args,
    status: result.status ?? 0,
    signal: result.signal ?? null,
    stdout: result.stdout ?? "",
    stderr: result.stderr ?? "",
    error: result.error ?? null
  };
}

export function runCommandChecked(command, args = [], options = {}) {
  const result = runCommand(command, args, options);
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(formatCommandFailure(result));
  }
  return result;
}

export function binaryAvailable(command, versionArgs = ["--version"], options = {}) {
  const result = runCommand(command, versionArgs, options);
  if (result.error && /** @type {NodeJS.ErrnoException} */ (result.error).code === "ENOENT") {
    return { available: false, detail: "not found" };
  }
  if (result.error) {
    return { available: false, detail: result.error.message };
  }
  if (result.status !== 0) {
    const detail = result.stderr.trim() || result.stdout.trim() || `exit ${result.status}`;
    return { available: false, detail };
  }
  return { available: true, detail: result.stdout.trim() || result.stderr.trim() || "ok" };
}

function looksLikeMissingProcessMessage(text) {
  return /not found|no running instance|cannot find|does not exist|no such process/i.test(text);
}

export function terminateProcessTree(pid, options = {}) {
  if (!Number.isFinite(pid)) {
    return { attempted: false, delivered: false, method: null };
  }

  const platform = options.platform ?? process.platform;
  const runCommandImpl = options.runCommandImpl ?? runCommand;
  const killImpl = options.killImpl ?? process.kill.bind(process);

  if (platform === "win32") {
    const result = runCommandImpl("taskkill", ["/PID", String(pid), "/T", "/F"], {
      cwd: options.cwd,
      env: options.env
    });

    if (!result.error && result.status === 0) {
      return { attempted: true, delivered: true, method: "taskkill", result };
    }

    const combinedOutput = `${result.stderr}\n${result.stdout}`.trim();
    if (!result.error && looksLikeMissingProcessMessage(combinedOutput)) {
      return { attempted: true, delivered: false, method: "taskkill", result };
    }

    if (result.error?.code === "ENOENT") {
      try {
        killImpl(pid);
        return { attempted: true, delivered: true, method: "kill" };
      } catch (error) {
        if (error?.code === "ESRCH") {
          return { attempted: true, delivered: false, method: "kill" };
        }
        throw error;
      }
    }

    if (result.error) {
      throw result.error;
    }

    throw new Error(formatCommandFailure(result));
  }

  try {
    killImpl(-pid, "SIGTERM");
    return { attempted: true, delivered: true, method: "process-group" };
  } catch (error) {
    if (error?.code !== "ESRCH") {
      try {
        killImpl(pid, "SIGTERM");
        return { attempted: true, delivered: true, method: "process" };
      } catch (innerError) {
        if (innerError?.code === "ESRCH") {
          return { attempted: true, delivered: false, method: "process" };
        }
        throw innerError;
      }
    }

    return { attempted: true, delivered: false, method: "process-group" };
  }
}

export function formatCommandFailure(result) {
  const parts = [`${result.command} ${result.args.join(" ")}`.trim()];
  if (result.signal) {
    parts.push(`signal=${result.signal}`);
  } else {
    parts.push(`exit=${result.status}`);
  }
  const stderr = (result.stderr || "").trim();
  const stdout = (result.stdout || "").trim();
  if (stderr) {
    parts.push(stderr);
  } else if (stdout) {
    parts.push(stdout);
  }
  return parts.join(": ");
}
