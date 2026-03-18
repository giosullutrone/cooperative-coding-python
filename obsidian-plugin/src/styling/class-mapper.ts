// src/styling/class-mapper.ts
import type { CcodingMetadata, EdgeMetadata } from "../types";

const KIND_CLASS_MAP: Record<string, string> = {
  class: "ccoding-node-class",
  method: "ccoding-node-method",
  field: "ccoding-node-field",
  package: "ccoding-node-package",
};

const RELATION_CLASS_MAP: Record<string, string> = {
  inherits: "ccoding-edge-inherits",
  implements: "ccoding-edge-implements",
  composes: "ccoding-edge-composes",
  depends: "ccoding-edge-depends",
  calls: "ccoding-edge-calls",
  detail: "ccoding-edge-detail",
  context: "ccoding-edge-context",
};

/**
 * Compute CSS class list for a ccoding canvas node.
 * Pure function — no DOM or Obsidian dependency.
 */
export function nodeClasses(
  meta: CcodingMetadata,
  showRejected: boolean,
): string[] {
  const classes: string[] = ["ccoding-node"];

  // Kind-based styling
  if (meta.kind && KIND_CLASS_MAP[meta.kind]) {
    classes.push(KIND_CLASS_MAP[meta.kind]);
  }

  // Status-based styling
  switch (meta.status) {
    case "proposed":
      classes.push("ccoding-ghost");
      break;
    case "rejected":
      classes.push("ccoding-rejected");
      if (!showRejected) {
        classes.push("ccoding-rejected-hidden");
      }
      break;
    case "accepted":
      classes.push("ccoding-accepted");
      break;
    case "stale":
      classes.push("ccoding-stale");
      break;
  }

  return classes;
}

/**
 * Compute CSS class list for a ccoding canvas edge.
 */
export function edgeClasses(meta: EdgeMetadata): string[] {
  const classes: string[] = ["ccoding-edge"];

  if (RELATION_CLASS_MAP[meta.relation]) {
    classes.push(RELATION_CLASS_MAP[meta.relation]);
  }

  if (meta.status === "proposed") {
    classes.push("ccoding-ghost");
  }

  return classes;
}
