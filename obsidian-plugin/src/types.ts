// src/types.ts

/** ccoding metadata on a canvas node. */
export interface CcodingMetadata {
  kind?: string;         // "class" | "method" | "field" | "package"
  stereotype?: string;   // "protocol" | "dataclass" | "abstract" | "enum"
  language?: string;
  source?: string;
  qualifiedName?: string;
  status?: string;       // "accepted" | "proposed" | "rejected" | "stale"
  proposedBy?: string | null;
  proposalRationale?: string | null;
  layoutPending?: boolean;
}

/** ccoding metadata on a canvas edge. */
export interface EdgeMetadata {
  relation: string;      // "inherits" | "implements" | "composes" | "depends" | "calls" | "detail" | "context"
  status?: string;
  proposedBy?: string | null;
  proposalRationale?: string | null;
}

/** Result of a CLI command execution. */
export interface CommandResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
}

/** Plugin settings persisted by Obsidian. */
export interface PluginSettings {
  ccodingPath: string;
  projectRoot: string;
  showRejectedNodes: boolean;
  autoReloadOnChange: boolean;
  commandTimeout: number;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  ccodingPath: "",
  projectRoot: "",
  showRejectedNodes: false,
  autoReloadOnChange: true,
  commandTimeout: 30000,
};

/**
 * Parse raw ccoding metadata from a canvas node's JSON.
 * Returns null if the input is not a valid metadata object.
 */
export function parseCcodingMetadata(
  raw: unknown,
): CcodingMetadata | null {
  if (raw == null || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  // Must have at least status or kind to be ccoding metadata
  if (!obj.status && !obj.kind) return null;
  return {
    kind: typeof obj.kind === "string" ? obj.kind : undefined,
    stereotype: typeof obj.stereotype === "string" ? obj.stereotype : undefined,
    language: typeof obj.language === "string" ? obj.language : undefined,
    source: typeof obj.source === "string" ? obj.source : undefined,
    qualifiedName:
      typeof obj.qualifiedName === "string" ? obj.qualifiedName : undefined,
    status: typeof obj.status === "string" ? obj.status : undefined,
    proposedBy:
      typeof obj.proposedBy === "string" ? obj.proposedBy : null,
    proposalRationale:
      typeof obj.proposalRationale === "string"
        ? obj.proposalRationale
        : null,
    layoutPending: obj.layoutPending === true,
  };
}

/**
 * Parse raw ccoding metadata from a canvas edge's JSON.
 */
export function parseEdgeMetadata(
  raw: unknown,
): EdgeMetadata | null {
  if (raw == null || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.relation !== "string") return null;
  return {
    relation: obj.relation,
    status: typeof obj.status === "string" ? obj.status : undefined,
    proposedBy:
      typeof obj.proposedBy === "string" ? obj.proposedBy : null,
    proposalRationale:
      typeof obj.proposalRationale === "string"
        ? obj.proposalRationale
        : null,
  };
}
