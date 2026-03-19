// src/watcher/canvas-watcher.ts
import { debounce, type Vault, type TAbstractFile, type EventRef } from "obsidian";

/**
 * Watches a canvas file for external modifications using Obsidian's vault events.
 * Uses Obsidian's built-in debounce for coalescing rapid changes.
 */
export class CanvasWatcher {
  private filePath: string | null = null;
  private vault: Vault | null = null;
  private modifyRef: EventRef | null = null;
  private deleteRef: EventRef | null = null;
  private renameRef: EventRef | null = null;
  private debouncedReload: ReturnType<typeof debounce>;

  constructor(
    private onReload: () => void,
    private onDeleted: (() => void) | null = null,
    debounceMs = 300,
  ) {
    this.debouncedReload = debounce(() => {
      this.onReload();
    }, debounceMs, true);
  }

  /**
   * Start watching a canvas file via Obsidian vault events.
   * @param vault - The Obsidian vault instance
   * @param vaultRelativePath - Path relative to vault root (e.g. "design.canvas")
   */
  start(vault: Vault, vaultRelativePath: string): void {
    this.stop();
    this.vault = vault;
    this.filePath = vaultRelativePath;

    this.modifyRef = vault.on("modify", (file: TAbstractFile) => {
      if (file.path === this.filePath) {
        this.debouncedReload();
      }
    });

    this.deleteRef = vault.on("delete", (file: TAbstractFile) => {
      if (file.path === this.filePath) {
        this.stop();
        this.onDeleted?.();
      }
    });

    this.renameRef = vault.on("rename", (file: TAbstractFile, oldPath: string) => {
      if (oldPath === this.filePath) {
        this.stop();
        this.onDeleted?.();
      }
    });
  }

  stop(): void {
    if (this.vault) {
      if (this.modifyRef) this.vault.offref(this.modifyRef);
      if (this.deleteRef) this.vault.offref(this.deleteRef);
      if (this.renameRef) this.vault.offref(this.renameRef);
    }
    this.modifyRef = null;
    this.deleteRef = null;
    this.renameRef = null;
    this.filePath = null;
    this.vault = null;
  }

  getFilePath(): string | null {
    return this.filePath;
  }
}
