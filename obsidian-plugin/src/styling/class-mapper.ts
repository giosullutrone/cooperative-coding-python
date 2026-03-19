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
  const attrs: Record<string, string | undefined> = {};

  if (meta.kind) attrs["data-ccoding-kind"] = meta.kind;
  if (meta.status) attrs["data-ccoding-status"] = meta.status;
  if (meta.stereotype) attrs["data-ccoding-stereotype"] = meta.stereotype;

  if (meta.status === "rejected" && hideRejected) {
    attrs["data-ccoding-rejected-hidden"] = "true";
  }

  return attrs;
}

/**
 * Compute data-attribute map for a ccoding canvas edge.
 */
export function edgeAttributes(
  meta: EdgeMetadata,
): Record<string, string | undefined> {
  const attrs: Record<string, string | undefined> = {};

  if (meta.relation) attrs["data-ccoding-relation"] = meta.relation;
  if (meta.status) attrs["data-ccoding-status"] = meta.status;

  return attrs;
}
