// tests/sync/output-parser.test.ts
import { describe, it, expect } from "vitest";
import { parseSyncOutput, type SyncSummary } from "../../src/sync/output-parser";

describe("parseSyncOutput", () => {
  it("parses successful sync with changes", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({
        status: "ok",
        synced: [
          { qualifiedName: "UserService", action: "updated" },
          { qualifiedName: "AuthController", action: "created" },
        ],
        conflicts: [],
      }),
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.nodesUpdated).toBe(1);
    expect(summary.nodesCreated).toBe(1);
    expect(summary.conflicts).toBe(0);
    expect(summary.ok).toBe(true);
  });

  it("parses sync with conflicts", () => {
    const result = {
      success: false,
      stdout: JSON.stringify({
        status: "conflicts",
        synced: [],
        conflicts: [
          {
            qualifiedName: "UserService",
            elementKind: "class",
            elementId: "abc123",
            canvasSummary: "Added method parse()",
            codeSummary: "Changed method signature",
          },
        ],
      }),
      stderr: "",
      exitCode: 1,
    };

    const summary = parseSyncOutput(result);
    expect(summary.conflicts).toBe(1);
    expect(summary.ok).toBe(false);
  });

  it("returns raw fallback for non-JSON output", () => {
    const result = {
      success: true,
      stdout: "Already in sync.",
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.ok).toBe(true);
    expect(summary.rawOutput).toBe("Already in sync.");
  });

  it("handles empty stdout", () => {
    const result = {
      success: true,
      stdout: "",
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.ok).toBe(true);
  });

  it("formats a human-readable summary", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({
        status: "ok",
        synced: [
          { qualifiedName: "A", action: "updated" },
          { qualifiedName: "B", action: "updated" },
          { qualifiedName: "C", action: "created" },
        ],
        conflicts: [],
      }),
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.displayText).toContain("2 updated");
    expect(summary.displayText).toContain("1 created");
  });
});
