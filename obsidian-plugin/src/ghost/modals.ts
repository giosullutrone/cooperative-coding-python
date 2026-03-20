// src/ghost/modals.ts
import { Modal, Setting, App, Notice } from "obsidian";
import type { CcodingBridge, ProposeOptions, ProposeEdgeOptions } from "../bridge/cli";

export const NODE_KINDS = ["class", "interface", "module", "package"];
export const CHILD_KINDS = ["field", "method"];
export const ALL_KINDS = [...NODE_KINDS, ...CHILD_KINDS];
export const STEREOTYPES = ["", "protocol", "abstract", "dataclass", "enum"];
export const EDGE_RELATIONS = ["inherits", "implements", "composes", "depends", "calls", "detail", "context"];

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
        for (const k of ALL_KINDS) drop.addOption(k, k);
        drop.setValue(this.kind);
        drop.onChange((v) => { this.kind = v; });
      });

    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional — any value accepted")
      .addText((text) => {
        text.setPlaceholder("e.g., protocol, abstract, dataclass, enum");
        text.onChange((v) => { this.stereotype = v; });
        // Attach datalist for autocomplete suggestions
        const input = text.inputEl;
        const datalist = document.createElement("datalist");
        datalist.id = "ccoding-stereotype-suggestions";
        for (const s of STEREOTYPES.filter(Boolean)) {
          const opt = document.createElement("option");
          opt.value = s;
          datalist.appendChild(opt);
        }
        input.setAttribute("list", datalist.id);
        input.parentElement?.appendChild(datalist);
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
      .setDesc("Optional — any value accepted")
      .addText((text) => {
        text.setPlaceholder("e.g., protocol, abstract, dataclass, enum");
        text.onChange((v) => { this.stereotype = v; });
        const input = text.inputEl;
        const datalist = document.createElement("datalist");
        datalist.id = "ccoding-stereotype-elevate";
        for (const s of STEREOTYPES.filter(Boolean)) {
          const opt = document.createElement("option");
          opt.value = s;
          datalist.appendChild(opt);
        }
        input.setAttribute("list", datalist.id);
        input.parentElement?.appendChild(datalist);
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

// ─── Direct Canvas Manipulation Modals (no CLI needed) ─────────

export interface AddChildResult {
  kind: "field" | "method";
  name: string;
  typeName?: string;
  params?: string;
  returnType?: string;
  description?: string;
}

/**
 * Modal for adding a field or method as a child of a class/interface.
 * Works without the CLI — directly manipulates canvas data.
 */
export class AddChildModal extends Modal {
  private kind: "field" | "method";
  private name = "";
  private typeName = "";
  private params = "";
  private returnType = "";
  private description = "";

  constructor(
    app: App,
    private parentLabel: string,
    defaultKind: "field" | "method",
    private onDone: (result: AddChildResult) => void,
  ) {
    super(app);
    this.kind = defaultKind;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", {
      text: `Add ${this.kind} to "${this.parentLabel}"`,
    });

    new Setting(contentEl)
      .setName("Kind")
      .addDropdown((drop) => {
        for (const k of ["field", "method"]) drop.addOption(k, k);
        drop.setValue(this.kind);
        drop.onChange((v) => { this.kind = v as "field" | "method"; });
      });

    new Setting(contentEl)
      .setName("Name")
      .setDesc(this.kind === "field" ? "Field name" : "Method name")
      .addText((text) =>
        text.setPlaceholder(this.kind === "field" ? "my_field" : "my_method()").onChange((v) => {
          this.name = v;
        }),
      );

    new Setting(contentEl)
      .setName("Type / Parameters")
      .setDesc("For fields: type annotation. For methods: parameter list")
      .addText((text) =>
        text.setPlaceholder("str | x: int, y: int").onChange((v) => {
          if (this.kind === "field") this.typeName = v;
          else this.params = v;
        }),
      );

    new Setting(contentEl)
      .setName("Return type")
      .setDesc("For methods only")
      .addText((text) =>
        text.setPlaceholder("bool").onChange((v) => { this.returnType = v; }),
      );

    new Setting(contentEl)
      .setName("Description")
      .setDesc("Optional description or pseudocode")
      .addTextArea((area) =>
        area.setPlaceholder("...").onChange((v) => { this.description = v; }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Add").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private submit(): void {
    if (!this.name.trim()) {
      new Notice("Name is required.");
      return;
    }
    this.close();
    this.onDone({
      kind: this.kind,
      name: this.name.trim(),
      typeName: this.typeName.trim() || undefined,
      params: this.params.trim() || undefined,
      returnType: this.returnType.trim() || undefined,
      description: this.description.trim() || undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

export interface CreateElementResult {
  kind: string;
  name: string;
  stereotype?: string;
  description?: string;
}

/**
 * Modal for creating a new ccoding element directly on the canvas.
 * Works without the CLI — directly manipulates canvas data.
 */
export class CreateElementModal extends Modal {
  private kind = "class";
  private name = "";
  private stereotype = "";
  private description = "";

  constructor(
    app: App,
    defaultKind?: string,
    private onDone?: (result: CreateElementResult) => void,
  ) {
    super(app);
    if (defaultKind) this.kind = defaultKind;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "Create new element" });

    new Setting(contentEl)
      .setName("Name")
      .setDesc("Element name")
      .addText((text) =>
        text.setPlaceholder("MyClass").onChange((v) => { this.name = v; }),
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
      .setDesc("Optional — any value accepted")
      .addText((text) => {
        text.setPlaceholder("e.g., protocol, abstract, dataclass, enum");
        text.onChange((v) => { this.stereotype = v; });
        const input = text.inputEl;
        const datalist = document.createElement("datalist");
        datalist.id = "ccoding-stereotype-create";
        for (const s of STEREOTYPES.filter(Boolean)) {
          const opt = document.createElement("option");
          opt.value = s;
          datalist.appendChild(opt);
        }
        input.setAttribute("list", datalist.id);
        input.parentElement?.appendChild(datalist);
      });

    new Setting(contentEl)
      .setName("Description")
      .setDesc("Optional description")
      .addTextArea((area) =>
        area.setPlaceholder("What does this element do?").onChange((v) => {
          this.description = v;
        }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Create").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private submit(): void {
    if (!this.name.trim()) {
      new Notice("Name is required.");
      return;
    }
    this.close();
    this.onDone?.({
      kind: this.kind,
      name: this.name.trim(),
      stereotype: this.stereotype || undefined,
      description: this.description.trim() || undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

export interface AddRelationResult {
  targetId: string;
  relation: string;
  label?: string;
}

/**
 * Modal for adding a relation (edge) between two ccoding nodes.
 * Works without the CLI — directly manipulates canvas data.
 */
export class AddRelationModal extends Modal {
  private targetId = "";
  private relation = "depends";
  private label = "";

  constructor(
    app: App,
    private sourceLabel: string,
    private sourceId: string,
    private availableTargets: Array<{ id: string; label: string }>,
    private onDone: (result: AddRelationResult) => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", {
      text: `Add relation from "${this.sourceLabel}"`,
    });

    new Setting(contentEl)
      .setName("Target")
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
      .addButton((btn) =>
        btn.setButtonText("Add Relation").setCta().onClick(() => this.submit()),
      )
      .addButton((btn) =>
        btn.setButtonText("Cancel").onClick(() => this.close()),
      );
  }

  private submit(): void {
    if (!this.targetId) {
      new Notice("Please select a target node.");
      return;
    }
    this.close();
    this.onDone({
      targetId: this.targetId,
      relation: this.relation,
      label: this.label.trim() || undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
