// src/ghost/restore-modal.ts
import { Modal, Setting, App } from "obsidian";

export type RestoreChoice =
  | { action: "restore" }
  | { action: "relink"; qualifiedName: string; source: string }
  | { action: "remove" };

/**
 * Modal for recovering a stale node.
 * Presents three options: restore code, re-link, or remove from canvas.
 */
export class RestoreModal extends Modal {
  private relinkName = "";
  private relinkSource = "";

  constructor(
    app: App,
    private nodeId: string,
    private qualifiedName: string,
    private sourcePath: string,
    private onDone: (choice: RestoreChoice) => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "Recover stale element" });

    contentEl.createEl("p", {
      text: `"${this.qualifiedName}" — this element's code was deleted or moved.`,
    });
    if (this.sourcePath) {
      contentEl.createEl("p", {
        text: `Expected source: ${this.sourcePath}`,
        cls: "setting-item-description",
      });
    }

    // Option 1: Restore code
    new Setting(contentEl)
      .setName("Restore code")
      .setDesc("Regenerate the code file from the canvas definition")
      .addButton((btn) =>
        btn.setButtonText("Restore").setCta().onClick(() => {
          this.close();
          this.onDone({ action: "restore" });
        }),
      );

    // Option 2: Re-link
    contentEl.createEl("h4", { text: "Re-link to different code" });

    new Setting(contentEl)
      .setName("New qualified name")
      .addText((text) =>
        text.setValue(this.qualifiedName)
          .onChange((v) => { this.relinkName = v; }),
      );

    new Setting(contentEl)
      .setName("New source path")
      .addText((text) =>
        text.setValue(this.sourcePath)
          .onChange((v) => { this.relinkSource = v; }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Re-link").onClick(() => {
          const name = this.relinkName.trim() || this.qualifiedName;
          const source = this.relinkSource.trim() || this.sourcePath;
          this.close();
          this.onDone({ action: "relink", qualifiedName: name, source });
        }),
      );

    // Option 3: Remove
    contentEl.createEl("hr");
    new Setting(contentEl)
      .setName("Remove from canvas")
      .setDesc("Delete this stale node and its edges permanently")
      .addButton((btn) =>
        btn.setButtonText("Remove").setWarning().onClick(() => {
          this.close();
          this.onDone({ action: "remove" });
        }),
      );
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
