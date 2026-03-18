// src/styling/class-mapper.ts
import type { CcodingMetadata, EdgeMetadata } from "../types";

/**
 * Compute CSS class list for a ccoding canvas node.
 * Pure function — no DOM or Obsidian dependency.
 *
 * Accepted nodes get no extra styling (they look like normal canvas nodes).
 * Only proposed/rejected/stale get visual treatment.
 */
export function nodeClasses(
  meta: CcodingMetadata,
  showRejected: boolean,
): string[] {
  const classes: string[] = ["ccoding-node"];

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
 * Only ghost edges get extra styling.
 */
export function edgeClasses(meta: EdgeMetadata): string[] {
  const classes: string[] = ["ccoding-edge"];

  if (meta.status === "proposed") {
    classes.push("ccoding-ghost");
  }

  return classes;
}
