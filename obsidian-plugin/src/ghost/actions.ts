// src/ghost/actions.ts
import { Notice } from "obsidian";
import type { CcodingBridge } from "../bridge/cli";

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
): Promise<void> {
  await runAction(bridge, () => bridge.sync(), "Syncing canvas");
}

export async function checkStatus(
  bridge: CcodingBridge,
): Promise<void> {
  const result = await bridge.status();
  if (result.success) {
    new Notice(result.stdout || "In sync", 5000);
  } else {
    new Notice(`Error: ${result.stderr}`, 5000);
  }
}

export function showRationale(rationale: string | null): void {
  if (rationale) {
    new Notice(`Agent rationale: ${rationale}`, 10000);
  } else {
    new Notice("No rationale provided.", 3000);
  }
}
