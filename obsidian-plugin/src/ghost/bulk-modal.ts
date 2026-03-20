// src/ghost/bulk-modal.ts
import { Modal, Setting, App, Notice } from "obsidian";
import type { CcodingBridge } from "../bridge/cli";

interface ProposalItem {
  id: string;
  name: string;
  kind: string;
  rationale: string;
  isEdge: boolean;
}

/**
 * Modal for selectively accepting/rejecting proposals.
 * Shows a filterable list with checkboxes.
 */
export class BulkOperationsModal extends Modal {
  private items: ProposalItem[] = [];
  private selected = new Set<string>();
  private kindFilter = "all";
  private searchFilter = "";

  constructor(
    app: App,
    private canvasData: any,
    private bridge: CcodingBridge,
    private onDone: () => void,
  ) {
    super(app);
    this.extractProposals();
  }

  private extractProposals(): void {
    // Extract proposed nodes
    for (const node of this.canvasData.nodes ?? []) {
      if (node.ccoding?.status !== "proposed") continue;
      this.items.push({
        id: node.id,
        name: node.ccoding.qualifiedName || node.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim() || node.id,
        kind: node.ccoding.kind || "unknown",
        rationale: node.ccoding.proposalRationale || "",
        isEdge: false,
      });
    }

    // Extract proposed edges
    for (const edge of this.canvasData.edges ?? []) {
      if (edge.ccoding?.status !== "proposed") continue;
      this.items.push({
        id: edge.id,
        name: edge.label || `${edge.ccoding.relation} edge`,
        kind: edge.ccoding.relation || "edge",
        rationale: edge.ccoding.proposalRationale || "",
        isEdge: true,
      });
    }
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: `Manage Proposals (${this.items.length})` });

    if (this.items.length === 0) {
      contentEl.createEl("p", { text: "No pending proposals." });
      return;
    }

    // Filter bar
    new Setting(contentEl)
      .setName("Filter by kind")
      .addDropdown((drop) => {
        drop.addOption("all", "All");
        const kinds = [...new Set(this.items.map((i) => i.kind))];
        for (const k of kinds) drop.addOption(k, k);
        drop.onChange((v) => {
          this.kindFilter = v;
          this.renderList(listEl);
        });
      })
      .addText((text) =>
        text.setPlaceholder("Search...").onChange((v) => {
          this.searchFilter = v.toLowerCase();
          this.renderList(listEl);
        }),
      );

    // Select All toggle
    new Setting(contentEl)
      .setName("Select All")
      .addToggle((toggle) =>
        toggle.onChange((v) => {
          if (v) {
            this.getFilteredItems().forEach((i) => this.selected.add(i.id));
          } else {
            this.selected.clear();
          }
          this.renderList(listEl);
        }),
      );

    // Scrollable list
    const listEl = contentEl.createDiv({ cls: "ccoding-bulk-list" });
    listEl.style.maxHeight = "400px";
    listEl.style.overflowY = "auto";
    this.renderList(listEl);

    // Footer
    const footer = new Setting(contentEl);
    footer.addButton((btn) =>
      btn.setButtonText("Accept Selected").setCta().onClick(() => this.execute("accept")),
    );
    footer.addButton((btn) =>
      btn.setButtonText("Reject Selected").setWarning().onClick(() => this.execute("reject")),
    );
    footer.addButton((btn) =>
      btn.setButtonText("Cancel").onClick(() => this.close()),
    );
  }

  private getFilteredItems(): ProposalItem[] {
    return this.items.filter((item) => {
      if (this.kindFilter !== "all" && item.kind !== this.kindFilter) return false;
      if (this.searchFilter && !item.name.toLowerCase().includes(this.searchFilter)) return false;
      return true;
    });
  }

  private renderList(container: HTMLElement): void {
    container.empty();
    const filtered = this.getFilteredItems();

    for (const item of filtered) {
      const row = new Setting(container);
      row.setName(`${item.name}`);
      row.setDesc(`${item.kind}${item.rationale ? ` — ${item.rationale}` : ""}`);
      row.addToggle((toggle) =>
        toggle.setValue(this.selected.has(item.id)).onChange((v) => {
          if (v) this.selected.add(item.id);
          else this.selected.delete(item.id);
        }),
      );
    }

    if (filtered.length === 0) {
      container.createEl("p", { text: "No proposals match the filter.", cls: "setting-item-description" });
    }
  }

  private async execute(action: "accept" | "reject"): Promise<void> {
    if (this.selected.size === 0) {
      new Notice("No items selected.");
      return;
    }

    this.close();

    const label = action === "accept" ? "Accepting" : "Rejecting";
    const notice = new Notice(`${label} ${this.selected.size} proposals...`, 0);

    try {
      for (const id of this.selected) {
        if (action === "accept") {
          await this.bridge.accept(id);
        } else {
          await this.bridge.reject(id);
        }
      }
      notice.hide();
      new Notice(`${action === "accept" ? "Accepted" : "Rejected"} ${this.selected.size} proposals`, 3000);
      this.onDone();
    } catch (err: any) {
      notice.hide();
      new Notice(`Error: ${err.message}`, 5000);
      this.onDone();
    }
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
