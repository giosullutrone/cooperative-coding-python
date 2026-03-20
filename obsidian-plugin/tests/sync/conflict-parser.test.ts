// tests/sync/conflict-parser.test.ts
import { describe, it, expect } from "vitest";
import { parseConflictOutput, type ConflictInfo } from "../../src/sync/conflict-parser";

describe("parseConflictOutput", () => {
  it("extracts conflicts from JSON output", () => {
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
            codeSummary: "Changed method signature of process()",
          },
          {
            qualifiedName: "AuthController",
            elementKind: "class",
            elementId: "def456",
            canvasSummary: "Renamed to LoginController",
            codeSummary: "Added new dependency",
          },
        ],
      }),
      stderr: "",
      exitCode: 1,
    };

    const conflicts = parseConflictOutput(result);
    expect(conflicts).toHaveLength(2);
    expect(conflicts[0].qualifiedName).toBe("UserService");
    expect(conflicts[0].elementKind).toBe("class");
    expect(conflicts[0].elementId).toBe("abc123");
    expect(conflicts[0].canvasSummary).toBe("Added method parse()");
    expect(conflicts[0].codeSummary).toBe("Changed method signature of process()");
  });

  it("returns empty array for non-JSON output", () => {
    const result = {
      success: false,
      stdout: "Error: something went wrong",
      stderr: "",
      exitCode: 1,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });

  it("returns empty array for successful sync with no conflicts", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({ status: "ok", synced: [], conflicts: [] }),
      stderr: "",
      exitCode: 0,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });

  it("returns empty array when conflicts field is missing", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({ status: "ok", synced: [] }),
      stderr: "",
      exitCode: 0,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });
});
