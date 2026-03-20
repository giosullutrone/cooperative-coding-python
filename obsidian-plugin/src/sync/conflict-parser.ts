// src/sync/conflict-parser.ts
import type { CommandResult } from "../types";

export interface ConflictInfo {
  qualifiedName: string;
  elementKind: string;
  elementId: string;
  canvasSummary: string;
  codeSummary: string;
}

/**
 * Parse conflict information from `ccoding sync --json` output.
 * Returns an empty array if the output is not JSON or has no conflicts.
 */
export function parseConflictOutput(result: CommandResult): ConflictInfo[] {
  try {
    const json = JSON.parse(result.stdout.trim());
    const conflicts = json.conflicts;
    if (!Array.isArray(conflicts)) return [];

    return conflicts.map((c: any) => ({
      qualifiedName: String(c.qualifiedName ?? ""),
      elementKind: String(c.elementKind ?? ""),
      elementId: String(c.elementId ?? ""),
      canvasSummary: String(c.canvasSummary ?? ""),
      codeSummary: String(c.codeSummary ?? ""),
    }));
  } catch {
    return [];
  }
}
