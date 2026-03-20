// src/ghost/actions.ts
import { Notice } from "obsidian";
import type { App } from "obsidian";
import type { CcodingBridge } from "../bridge/cli";
import { parseSyncOutput } from "../sync/output-parser";
import { parseConflictOutput } from "../sync/conflict-parser";
import {
  ConflictResolutionModal,
  type ConflictResolution,
} from "../sync/conflict-modal";

const BUSY_PATTERNS = ["locked", "busy", "EBUSY", "EAGAIN"];

function isBusyError(stderr: string): boolean {
  return BUSY_PATTERNS.some((p) => stderr.toLowerCase().includes(p.toLowerCase()));
}

/**
 * Execute a ghost action, showing user feedback via Notices.
 * If the canvas file is locked/busy, retries once after 500ms.
 */
async function runAction(
  bridge: CcodingBridge,
  action: () => Promise<any>,
  label: string,
): Promise<void> {
  const notice = new Notice(`${label}...`, 0);
  try {
    let result = await action();
    if (!result.success && isBusyError(result.stderr)) {
      // Retry once after 500ms
      await new Promise((r) => setTimeout(r, 500));
      result = await action();
    }
    notice.hide();
    if (!result.success) {
      const msg = isBusyError(result.stderr)
        ? "Canvas file is busy. Try again."
        : `Error: ${result.stderr}`;
      new Notice(msg, 5000);
    }
  } catch (err: any) {
    notice.hide();
    new Notice(`Error: ${err.message}`, 5000);
  }
}

/** Accept a node or edge by ID. */
export async function acceptElement(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(bridge, () => bridge.accept(id), "Accepting proposal");
}

/** Reject a node or edge by ID. */
export async function rejectElement(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(bridge, () => bridge.reject(id), "Rejecting proposal");
}

/** Reconsider a rejected node or edge by ID. */
export async function reconsiderElement(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(
    bridge,
    () => bridge.reconsider(id),
    "Reconsidering proposal",
  );
}

/** Restore a stale node to accepted status. */
export async function restoreElement(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(bridge, () => bridge.restore(id), "Restoring stale element");
}

export async function acceptAll(bridge: CcodingBridge): Promise<void> {
  await runAction(
    bridge,
    () => bridge.acceptAll(),
    "Accepting all proposals",
  );
}

export async function rejectAll(bridge: CcodingBridge): Promise<void> {
  await runAction(
    bridge,
    () => bridge.rejectAll(),
    "Rejecting all proposals",
  );
}

export async function syncCanvas(
  bridge: CcodingBridge,
  app?: App,
): Promise<void> {
  const notice = new Notice("Syncing canvas...", 0);
  try {
    let result = await bridge.syncJson();

    // Retry once on busy error (preserves existing behavior)
    if (!result.success && isBusyError(result.stderr)) {
      await new Promise((r) => setTimeout(r, 500));
      result = await bridge.syncJson();
    }

    notice.hide();

    if (!result.success && isBusyError(result.stderr)) {
      new Notice("Canvas file is busy. Try again.", 5000);
      return;
    }

    const summary = parseSyncOutput(result);

    // Check for conflicts
    const conflicts = parseConflictOutput(result);
    if (conflicts.length > 0 && app) {
      new ConflictResolutionModal(app, conflicts, async (resolutions) => {
        await applyConflictResolutions(bridge, resolutions);
      }).open();
      return;
    }

    // No conflicts — show structured summary
    new Notice(summary.displayText, 5000);
  } catch (err: any) {
    notice.hide();
    new Notice(`Error: ${err.message}`, 5000);
  }
}

/** Apply conflict resolutions then re-sync. */
async function applyConflictResolutions(
  bridge: CcodingBridge,
  resolutions: ConflictResolution[],
): Promise<void> {
  const notice = new Notice("Applying resolutions...", 0);
  try {
    for (const { conflict, resolution } of resolutions) {
      if (resolution === "keep-code") {
        // Get code version as canvas-formatted markdown, then set it
        const showResult = await bridge.show(conflict.qualifiedName);
        if (showResult.success) {
          await bridge.setText(conflict.elementId, showResult.stdout);
        }
      }
      // "keep-canvas" needs no action — canvas already has desired version
    }

    // Re-sync to complete non-conflicted changes
    const result = await bridge.syncJson();
    notice.hide();

    const summary = parseSyncOutput(result);
    new Notice(summary.displayText, 5000);
  } catch (err: any) {
    notice.hide();
    new Notice(`Error applying resolutions: ${err.message}`, 5000);
  }
}

export async function checkStatus(
  bridge: CcodingBridge,
): Promise<void> {
  try {
    const result = await bridge.statusJson();
    if (!result.success) {
      new Notice(`Error: ${result.stderr}`, 5000);
      return;
    }
    const summary = parseSyncOutput(result);
    new Notice(summary.displayText || "In sync", 5000);
  } catch (err: any) {
    new Notice(`Error: ${err.message}`, 5000);
  }
}
