// tests/bridge/cli.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CcodingBridge } from "../../src/bridge/cli";
import type { PluginSettings } from "../../src/types";
import { DEFAULT_SETTINGS } from "../../src/types";

// Mock child_process
vi.mock("child_process", () => ({
  execFile: vi.fn(),
}));

import { execFile } from "child_process";

function mockExecFile(
  stdout: string,
  stderr: string,
  exitCode: number,
) {
  (execFile as any).mockImplementation(
    (
      _cmd: string,
      _args: string[],
      _opts: any,
      cb: (err: any, stdout: string, stderr: string) => void,
    ) => {
      if (exitCode !== 0) {
        const err = new Error(stderr) as any;
        err.code = exitCode;
        cb(err, stdout, stderr);
      } else {
        cb(null, stdout, stderr);
      }
      return { stdin: { write: vi.fn(), end: vi.fn() } };
    },
  );
}

/** Capture the last execFile call args. */
function lastCallArgs(): string[] {
  const calls = (execFile as any).mock.calls;
  return calls[calls.length - 1][1]; // args parameter
}

describe("CcodingBridge", () => {
  let bridge: CcodingBridge;
  let settings: PluginSettings;

  beforeEach(() => {
    vi.clearAllMocks();
    settings = { ...DEFAULT_SETTINGS, projectRoot: "/test/project" };
    bridge = new CcodingBridge(settings);
    bridge.setVaultBasePath("/test/vault");
  });

  it("constructs accept command correctly", async () => {
    mockExecFile("", "", 0);
    await bridge.accept("node-abc123");
    expect(execFile).toHaveBeenCalledWith(
      "ccoding",
      ["--project", "/test/project", "accept", "node-abc123"],
      expect.objectContaining({ timeout: 30000 }),
      expect.any(Function),
    );
  });

  it("uses custom CLI path when set", async () => {
    settings.ccodingPath = "/custom/bin/ccoding";
    bridge = new CcodingBridge(settings);
    mockExecFile("", "", 0);
    await bridge.accept("node-1");
    expect(execFile).toHaveBeenCalledWith(
      "/custom/bin/ccoding",
      expect.any(Array),
      expect.any(Object),
      expect.any(Function),
    );
  });

  it("returns success result on exit 0", async () => {
    mockExecFile("output text", "", 0);
    const result = await bridge.status();
    expect(result.success).toBe(true);
    expect(result.stdout).toBe("output text");
    expect(result.exitCode).toBe(0);
  });

  it("returns failure result on non-zero exit", async () => {
    mockExecFile("", "error message", 1);
    const result = await bridge.accept("node-1");
    expect(result.success).toBe(false);
    expect(result.stderr).toBe("error message");
  });

  it("isAvailable returns true when CLI responds", async () => {
    mockExecFile("ccoding 0.1.0", "", 0);
    expect(await bridge.isAvailable()).toBe(true);
  });

  it("isAvailable returns false when CLI not found", async () => {
    (execFile as any).mockImplementation(
      (_cmd: string, _args: string[], _opts: any, cb: Function) => {
        const err = new Error("ENOENT") as any;
        err.code = "ENOENT";
        cb(err, "", "");
      },
    );
    expect(await bridge.isAvailable()).toBe(false);
  });

  // --- New bridge method tests ---

  it("constructs propose command with all options", async () => {
    mockExecFile("node-new-123", "", 0);
    await bridge.propose({
      kind: "class",
      name: "MyClass",
      stereotype: "abstract",
      rationale: "Need this for caching",
    });
    const args = lastCallArgs();
    expect(args).toContain("propose");
    expect(args).toContain("--kind");
    expect(args).toContain("class");
    expect(args).toContain("--name");
    expect(args).toContain("MyClass");
    expect(args).toContain("--stereotype");
    expect(args).toContain("abstract");
    expect(args).toContain("--rationale");
    expect(args).toContain("Need this for caching");
  });

  it("constructs propose command without optional args", async () => {
    mockExecFile("node-new-456", "", 0);
    await bridge.propose({ kind: "interface", name: "Parser" });
    const args = lastCallArgs();
    expect(args).toContain("propose");
    expect(args).toContain("--name");
    expect(args).toContain("Parser");
    expect(args).not.toContain("--stereotype");
    expect(args).not.toContain("--rationale");
  });

  it("constructs propose-edge command correctly", async () => {
    mockExecFile("edge-new-789", "", 0);
    await bridge.proposeEdge({
      from: "node-a",
      to: "node-b",
      relation: "inherits",
      label: "extends",
      rationale: "Parent class",
    });
    const args = lastCallArgs();
    expect(args).toContain("propose-edge");
    expect(args).toContain("--from");
    expect(args).toContain("node-a");
    expect(args).toContain("--to");
    expect(args).toContain("node-b");
    expect(args).toContain("--relation");
    expect(args).toContain("inherits");
    expect(args).toContain("--label");
    expect(args).toContain("extends");
  });

  it("calls ghosts command", async () => {
    mockExecFile("2 proposals pending", "", 0);
    const result = await bridge.ghosts();
    expect(result.success).toBe(true);
    const args = lastCallArgs();
    expect(args).toContain("ghosts");
  });

  it("calls diff command", async () => {
    mockExecFile("no changes", "", 0);
    const result = await bridge.diff();
    expect(result.success).toBe(true);
    const args = lastCallArgs();
    expect(args).toContain("diff");
  });

  it("calls show command with qualified name", async () => {
    mockExecFile("class content", "", 0);
    await bridge.show("parser.DocumentParser");
    const args = lastCallArgs();
    expect(args).toContain("show");
    expect(args).toContain("parser.DocumentParser");
  });
});
