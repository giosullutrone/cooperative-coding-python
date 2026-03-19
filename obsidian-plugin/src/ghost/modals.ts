// src/ghost/modals.ts
import { Modal, Setting, App, Notice } from "obsidian";
import type { CcodingBridge, ProposeOptions, ProposeEdgeOptions } from "../bridge/cli";

const NODE_KINDS = ["class", "interface", "module", "package"];
const STEREOTYPES = ["", "protocol", "abstract", "dataclass", "enum"];
const EDGE_RELATIONS = ["inherits", "implements", "composes", "depends", "calls", "detail", "context"];

/**
 * Modal for proposing a new ghost node.
 * Collects name, kind, stereotype, and rationale from the user.
 */
export class ProposeModal extends Modal {
  private name = "";
  private kind = "class";
  private stereotype = "";
  private rationale = "";

  constructor(
    app: App,
    private bridge: CcodingBridge,
    private onDone: () => void,
    defaultKind?: string,
  ) {
    super(app);
    if (defaultKind) this.kind = defaultKind;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "Propose new element" });

    new Setting(contentEl)
      .setName("Name")
      .setDesc("Class or component name")
      .addText((text) =>
        text.setPlaceholder("MyClass").onChange((v) => {
          this.name = v;
        }),
      );

    new Setting(contentEl)
      .setName("Kind")
      .addDropdown((drop) => {
        for (const k of NODE_KINDS) drop.addOption(k, k);
        drop.setValue(this.kind);
        drop.onChange((v) => { this.kind = v; });
      });

    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional: protocol, abstract, dataclass, enum")
      .addDropdown((drop) => {
        drop.addOption("", "(none)");
        for (const s of STEREOTYPES.filter(Boolean)) drop.addOption(s, s);
        drop.onChange((v) => { this.stereotype = v; });
      });

    new Setting(contentEl)
      .setName("Rationale")
      .setDesc("Why is this element being proposed?")
      .addTextArea((area) =>
        area.setPlaceholder("Reason for this proposal...").onChange((v) => {
          this.rationale = v;
        }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Propose").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private async submit(): Promise<void> {
    if (!this.name.trim()) {
      new Notice("Name is required.");
      return;
    }

    const opts: ProposeOptions = {
      kind: this.kind,
      name: this.name.trim(),
    };
    if (this.stereotype) opts.stereotype = this.stereotype;
    if (this.rationale.trim()) opts.rationale = this.rationale.trim();

    this.close();

    const notice = new Notice("Proposing element...", 0);
    const result = await this.bridge.propose(opts);
    notice.hide();

    if (result.success) {
      new Notice(`Proposed: ${this.name}`, 3000);
      this.onDone();
    } else {
      new Notice(`Error: ${result.stderr}`, 5000);
    }
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

/**
 * Modal for proposing a new ghost edge from a source node.
 * Lets the user pick the target node and relation type.
 */
export class ProposeEdgeModal extends Modal {
  private targetId = "";
  private relation = "depends";
  private label = "";
  private rationale = "";

  constructor(
    app: App,
    private bridge: CcodingBridge,
    private sourceId: string,
    private sourceLabel: string,
    private availableTargets: Array<{ id: string; label: string }>,
    private onDone: () => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", {
      text: `Propose edge from "${this.sourceLabel}"`,
    });

    new Setting(contentEl)
      .setName("Target node")
      .addDropdown((drop) => {
        drop.addOption("", "Select target...");
        for (const t of this.availableTargets) {
          if (t.id !== this.sourceId) {
            drop.addOption(t.id, t.label);
          }
        }
        drop.onChange((v) => { this.targetId = v; });
      });

    new Setting(contentEl)
      .setName("Relation")
      .addDropdown((drop) => {
        for (const r of EDGE_RELATIONS) drop.addOption(r, r);
        drop.setValue(this.relation);
        drop.onChange((v) => { this.relation = v; });
      });

    new Setting(contentEl)
      .setName("Label")
      .setDesc("Optional edge label")
      .addText((text) =>
        text.setPlaceholder("").onChange((v) => { this.label = v; }),
      );

    new Setting(contentEl)
      .setName("Rationale")
      .setDesc("Why is this relationship being proposed?")
      .addTextArea((area) =>
        area.setPlaceholder("Reason...").onChange((v) => { this.rationale = v; }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Propose Edge").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private async submit(): Promise<void> {
    if (!this.targetId) {
      new Notice("Please select a target node.");
      return;
    }

    const opts: ProposeEdgeOptions = {
      from: this.sourceId,
      to: this.targetId,
      relation: this.relation,
    };
    if (this.label.trim()) opts.label = this.label.trim();
    if (this.rationale.trim()) opts.rationale = this.rationale.trim();

    this.close();

    const notice = new Notice("Proposing edge...", 0);
    const result = await this.bridge.proposeEdge(opts);
    notice.hide();

    if (result.success) {
      new Notice(`Edge proposed: ${this.relation}`, 3000);
      this.onDone();
    } else {
      new Notice(`Error: ${result.stderr}`, 5000);
    }
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

/**
 * Modal for elevating a plain canvas node to a ccoding-tracked element.
 * Adds ccoding metadata to an existing node.
 */
export class ElevateModal extends Modal {
  private kind = "class";
  private stereotype = "";
  private nodeName = "";

  constructor(
    app: App,
    private nodeId: string,
    private currentText: string,
    private onDone: (meta: { kind: string; stereotype?: string; name: string }) => void,
  ) {
    super(app);
    // Guess the name from the node text (first line or first heading)
    const firstLine = currentText.split("\n")[0]?.replace(/^#+\s*/, "").trim() || "";
    this.nodeName = firstLine;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "Elevate to ccoding element" });

    new Setting(contentEl)
      .setName("Name")
      .setDesc("Element name (used for tracking)")
      .addText((text) =>
        text.setValue(this.nodeName).onChange((v) => { this.nodeName = v; }),
      );

    new Setting(contentEl)
      .setName("Kind")
      .addDropdown((drop) => {
        for (const k of NODE_KINDS) drop.addOption(k, k);
        drop.setValue(this.kind);
        drop.onChange((v) => { this.kind = v; });
      });

    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional")
      .addDropdown((drop) => {
        drop.addOption("", "(none)");
        for (const s of STEREOTYPES.filter(Boolean)) drop.addOption(s, s);
        drop.onChange((v) => { this.stereotype = v; });
      });

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Elevate").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private submit(): void {
    if (!this.nodeName.trim()) {
      new Notice("Name is required.");
      return;
    }
    this.close();
    this.onDone({
      kind: this.kind,
      name: this.nodeName.trim(),
      stereotype: this.stereotype || undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
