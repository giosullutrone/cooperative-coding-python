// src/styling/class-mapper.ts
import type { CcodingMetadata, EdgeMetadata } from "../types";

/**
 * Compute data-attribute map for a ccoding canvas node.
 * Pure function — no DOM or Obsidian dependency.
 * Returns a Record where keys are data-attribute names and values are strings.
 * Undefined values should not be set on the DOM element.
 */
export function nodeAttributes(
  meta: CcodingMetadata,
  hideRejected: boolean,
): Record<string, string | undefined> {
  // Always return all possible keys so stale attributes get cleared
  return {
    "data-ccoding-kind": meta.kind || undefined,
    "data-ccoding-status": meta.status || undefined,
    "data-ccoding-stereotype": meta.stereotype || undefined,
    "data-ccoding-has-proposed-changes": meta.proposedChanges ? "true" : undefined,
    "data-ccoding-rejected-hidden":
      meta.status === "rejected" && hideRejected ? "true" : undefined,
  };
}

/**
 * Compute data-attribute map for a ccoding canvas edge.
 */
export function edgeAttributes(
  meta: EdgeMetadata,
): Record<string, string | undefined> {
  // Always return all possible keys so stale attributes get cleared
  return {
    "data-ccoding-relation": meta.relation || undefined,
    "data-ccoding-status": meta.status || undefined,
    "data-ccoding-has-proposed-changes": meta.proposedChanges ? "true" : undefined,
  };
}
