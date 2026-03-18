import { watch, type FSWatcher } from "fs";
import { Debouncer } from "./debounce";

export class CanvasWatcher {
  private watcher: FSWatcher | null = null;
  private debouncer: Debouncer;
  private filePath: string | null = null;

  constructor(
    private onReload: () => void,
    private onDeleted: (() => void) | null = null,
    private debounceMs = 300,
  ) {
    this.debouncer = new Debouncer(() => {
      this.onReload();
    }, this.debounceMs);
  }

  start(filePath: string): void {
    this.stop();
    this.filePath = filePath;
    try {
      this.watcher = watch(filePath, (eventType) => {
        if (eventType === "rename") {
          // File was deleted or renamed
          this.stop();
          this.onDeleted?.();
          return;
        }
        this.debouncer.trigger();
      });
      this.watcher.on("error", () => {
        this.stop();
        this.onDeleted?.();
      });
    } catch {
      // File may not exist yet — that's OK
    }
  }

  stop(): void {
    this.debouncer.cancel();
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
    this.filePath = null;
  }

  getFilePath(): string | null {
    return this.filePath;
  }
}
