// src/sync/conflict-modal.ts
import { Modal, Setting, App, Notice } from "obsidian";
import type { ConflictInfo } from "./conflict-parser";

export type Resolution = "keep-canvas" | "keep-code" | "skip";

export interface ConflictResolution {
  conflict: ConflictInfo;
  resolution: Resolution;
}

/**
 * Modal for resolving sync conflicts.
 * Shows each conflict with canvas/code summaries and resolution buttons.
 */
export class ConflictResolutionModal extends Modal {
  private resolutions = new Map<string, Resolution>();

  constructor(
    app: App,
    private conflicts: ConflictInfo[],
    private onDone: (resolutions: ConflictResolution[]) => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", {
      text: `Sync Conflicts (${this.conflicts.length})`,
    });

    contentEl.createEl("p", {
      text: "Both canvas and code changed for these elements. Choose how to resolve each one.",
      cls: "setting-item-description",
    });

    for (const conflict of this.conflicts) {
      this.renderConflict(contentEl, conflict);
    }

    // Footer
    const footer = contentEl.createDiv({ cls: "ccoding-conflict-footer" });

    new Setting(footer)
      .addButton((btn) =>
        btn.setButtonText("Apply Resolutions").setCta().onClick(() => this.applyResolutions()),
      )
      .addButton((btn) =>
        btn.setButtonText("Skip All").onClick(() => this.close()),
      );
  }

  private renderConflict(container: HTMLElement, conflict: ConflictInfo): void {
    const section = container.createDiv({ cls: "ccoding-conflict-section" });

    // Header
    const header = section.createDiv({ cls: "ccoding-conflict-header" });
    header.createEl("strong", {
      text: `${conflict.qualifiedName} (${conflict.elementKind})`,
    });

    // Details
    const details = section.createDiv({ cls: "ccoding-conflict-details" });
    details.createEl("p", { text: `Canvas: ${conflict.canvasSummary}` });
    details.createEl("p", { text: `Code: ${conflict.codeSummary}` });

    // Resolution status
    const statusEl = section.createEl("span", {
      cls: "ccoding-conflict-status",
      text: "",
    });

    // Buttons
    const btnSetting = new Setting(section);

    btnSetting.addButton((btn) =>
      btn.setButtonText("Keep Canvas").onClick(() => {
        this.resolutions.set(conflict.elementId, "keep-canvas");
        statusEl.textContent = " ✓ Keep canvas";
      }),
    );

    btnSetting.addButton((btn) =>
      btn.setButtonText("Keep Code").onClick(() => {
        this.resolutions.set(conflict.elementId, "keep-code");
        statusEl.textContent = " ✓ Keep code";
      }),
    );

    btnSetting.addButton((btn) =>
      btn.setButtonText("Skip").onClick(() => {
        this.resolutions.set(conflict.elementId, "skip");
        statusEl.textContent = " — Skipped";
      }),
    );
  }

  private applyResolutions(): void {
    const hasNonSkip = Array.from(this.resolutions.values()).some(
      (r) => r !== "skip",
    );
    if (!hasNonSkip) {
      new Notice("No resolutions selected. Use Skip All to dismiss.");
      return;
    }

    const results: ConflictResolution[] = this.conflicts
      .filter((c) => {
        const r = this.resolutions.get(c.elementId);
        return r && r !== "skip";
      })
      .map((c) => ({
        conflict: c,
        resolution: this.resolutions.get(c.elementId)!,
      }));

    this.close();
    this.onDone(results);
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
