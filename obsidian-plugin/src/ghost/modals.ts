// src/ghost/modals.ts
import { Modal, Setting, App, Notice } from "obsidian";

export const NODE_KINDS = ["class", "interface", "module", "package"];
export const CHILD_KINDS = ["field", "method"];
export const ALL_KINDS = [...NODE_KINDS, ...CHILD_KINDS];
export const STEREOTYPES = ["", "protocol", "abstract", "dataclass", "enum"];
export const EDGE_RELATIONS = ["inherits", "implements", "composes", "depends", "calls", "detail", "context"];

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
  qualifiedName?: string;
  stereotype?: string;
  description?: string;
  language?: string;
  source?: string;
  status: string;
  proposedBy?: string;
  rationale?: string;
}

/**
 * Modal for creating a new ccoding element directly on the canvas.
 * Works without the CLI — directly manipulates canvas data.
 */
export class CreateElementModal extends Modal {
  private kind = "class";
  private name = "";
  private qualifiedName = "";
  private stereotype = "";
  private description = "";
  private language = "";
  private source = "";
  private status = "accepted";
  private proposedBy = "";
  private rationale = "";

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
      .setDesc("Display name for the element")
      .addText((text) =>
        text.setPlaceholder("MyClass").onChange((v) => { this.name = v; }),
      );

    new Setting(contentEl)
      .setName("Qualified name")
      .setDesc("Optional — full path (e.g., com.example.MyClass)")
      .addText((text) =>
        text.setPlaceholder("com.example.MyClass").onChange((v) => { this.qualifiedName = v; }),
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
      .setName("Language")
      .setDesc("Optional — overrides default language for this node")
      .addText((text) =>
        text.setPlaceholder("e.g., python, typescript")
          .onChange((v) => { this.language = v; }),
      );

    new Setting(contentEl)
      .setName("Source")
      .setDesc("Optional — path to source file")
      .addText((text) =>
        text.setPlaceholder("src/example.py").onChange((v) => { this.source = v; }),
      );

    new Setting(contentEl)
      .setName("Description")
      .setDesc("Optional description")
      .addTextArea((area) =>
        area.setPlaceholder("What does this element do?").onChange((v) => {
          this.description = v;
        }),
      );

    // Proposal fields — hidden by default, shown when status is "proposed"
    const proposalContainer = contentEl.createDiv();
    proposalContainer.style.display = "none";

    new Setting(proposalContainer)
      .setName("Proposed by")
      .setDesc("Who is proposing this element?")
      .addText((text) =>
        text.setPlaceholder("e.g., agent-name, your-name")
          .onChange((v) => { this.proposedBy = v; }),
      );

    new Setting(proposalContainer)
      .setName("Rationale")
      .setDesc("Why is this element being proposed?")
      .addTextArea((area) =>
        area.setPlaceholder("Reason for this proposal...").onChange((v) => {
          this.rationale = v;
        }),
      );

    new Setting(contentEl)
      .setName("Status")
      .setDesc("Accepted creates immediately; proposed creates a ghost node for review")
      .addDropdown((drop) => {
        drop.addOption("accepted", "accepted");
        drop.addOption("proposed", "proposed");
        drop.setValue(this.status);
        drop.onChange((v) => {
          this.status = v;
          proposalContainer.style.display = v === "proposed" ? "" : "none";
        });
      });

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
      qualifiedName: this.qualifiedName.trim() || undefined,
      stereotype: this.stereotype || undefined,
      description: this.description.trim() || undefined,
      language: this.language.trim() || undefined,
      source: this.source.trim() || undefined,
      status: this.status,
      proposedBy: this.status === "proposed" ? (this.proposedBy.trim() || "human") : undefined,
      rationale: this.status === "proposed" ? (this.rationale.trim() || undefined) : undefined,
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
  status: string;
  proposedBy?: string;
  rationale?: string;
}

/**
 * Modal for adding a relation (edge) between two ccoding nodes.
 * Works without the CLI — directly manipulates canvas data.
 */
export class AddRelationModal extends Modal {
  private targetId = "";
  private relation = "depends";
  private label = "";
  private status = "accepted";
  private proposedBy = "";
  private rationale = "";

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

    const proposalContainer = contentEl.createDiv();
    proposalContainer.style.display = "none";

    new Setting(proposalContainer)
      .setName("Proposed by")
      .setDesc("Who is proposing this relation?")
      .addText((text) =>
        text.setPlaceholder("e.g., agent-name, your-name")
          .onChange((v) => { this.proposedBy = v; }),
      );

    new Setting(proposalContainer)
      .setName("Rationale")
      .setDesc("Why is this relation being proposed?")
      .addTextArea((area) =>
        area.setPlaceholder("Reason...").onChange((v) => { this.rationale = v; }),
      );

    new Setting(contentEl)
      .setName("Status")
      .setDesc("Accepted creates immediately; proposed creates a ghost edge for review")
      .addDropdown((drop) => {
        drop.addOption("accepted", "accepted");
        drop.addOption("proposed", "proposed");
        drop.setValue(this.status);
        drop.onChange((v) => {
          this.status = v;
          proposalContainer.style.display = v === "proposed" ? "" : "none";
        });
      });

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
      status: this.status,
      proposedBy: this.status === "proposed" ? (this.proposedBy.trim() || "human") : undefined,
      rationale: this.status === "proposed" ? (this.rationale.trim() || undefined) : undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

export interface ConnectContextResult {
  targetId: string;
  label?: string;
}

/**
 * Modal for connecting a context node to a code element (or vice versa).
 * Creates a context edge — canvas-only, never synced.
 */
export class ConnectContextModal extends Modal {
  private targetId = "";
  private label = "";

  constructor(
    app: App,
    private sourceLabel: string,
    private sourceId: string,
    private availableTargets: Array<{ id: string; label: string }>,
    private onDone: (result: ConnectContextResult) => void,
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", {
      text: `Connect "${this.sourceLabel}" to...`,
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
      .setName("Label")
      .setDesc("Optional description for this context link")
      .addText((text) =>
        text.setPlaceholder("").onChange((v) => { this.label = v; }),
      );

    new Setting(contentEl)
      .addButton((btn) =>
        btn.setButtonText("Connect").setCta().onClick(() => this.submit()),
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
      label: this.label.trim() || undefined,
    });
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
