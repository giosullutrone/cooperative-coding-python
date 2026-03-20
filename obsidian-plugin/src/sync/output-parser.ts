// src/sync/output-parser.ts
import type { CommandResult } from "../types";

export interface SyncSummary {
  ok: boolean;
  nodesUpdated: number;
  nodesCreated: number;
  edgesUpdated: number;
  conflicts: number;
  rawOutput: string;
  displayText: string;
}

interface SyncJsonOutput {
  status: string;
  synced: Array<{ qualifiedName: string; action: string }>;
  conflicts: Array<unknown>;
}

/**
 * Parse the CLI sync/status output into a structured summary.
 * Expects JSON from `ccoding sync --json`. Falls back gracefully
 * for non-JSON output.
 */
export function parseSyncOutput(result: CommandResult): SyncSummary {
  const raw = result.stdout.trim();

  try {
    const json: SyncJsonOutput = JSON.parse(raw);

    const updated = json.synced.filter((s) => s.action === "updated").length;
    const created = json.synced.filter((s) => s.action === "created").length;
    const edgesUpdated = json.synced.filter((s) => s.action === "edge_updated").length;
    const conflicts = json.conflicts?.length ?? 0;

    const parts: string[] = [];
    if (updated > 0) parts.push(`${updated} updated`);
    if (created > 0) parts.push(`${created} created`);
    if (edgesUpdated > 0) parts.push(`${edgesUpdated} edges updated`);
    if (conflicts > 0) parts.push(`${conflicts} conflict${conflicts !== 1 ? "s" : ""}`);

    const displayText = parts.length > 0
      ? `Sync complete: ${parts.join(", ")}`
      : "Sync complete: no changes";

    return {
      ok: json.status !== "conflicts",
      nodesUpdated: updated,
      nodesCreated: created,
      edgesUpdated,
      conflicts,
      rawOutput: raw,
      displayText,
    };
  } catch {
    // Non-JSON output — fall back to raw text
    return {
      ok: result.success,
      nodesUpdated: 0,
      nodesCreated: 0,
      edgesUpdated: 0,
      conflicts: 0,
      rawOutput: raw,
      displayText: raw || "Sync complete",
    };
  }
}
