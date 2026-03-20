# Obsidian Plugin Spec Gap Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close all 9 identified gaps between the CooperativeCoding spec and the Obsidian plugin.

**Architecture:** Each gap is an independent, self-contained addition to the existing plugin. Changes follow established patterns: Modal classes for UI input, async action wrappers for CLI calls, data-attribute CSS styling, and pure helper functions for canvas manipulation. New parsers for CLI JSON output live in a `sync/` directory and are unit-testable.

**Tech Stack:** TypeScript, Obsidian Plugin API, vitest for testing, esbuild for bundling.

**Spec:** `docs/superpowers/specs/2026-03-20-obsidian-plugin-spec-gaps-design.md`

**Prerequisites:**
- **Commit existing changes first.** The git status shows uncommitted modifications to `ghost/actions.ts`, `ghost/modals.ts`, `main.ts`, and an untracked `canvas-helpers.ts`. Commit or stash these before starting this plan.
- The ccoding CLI must support `sync --json`, `status --json`, and `diff --json` flags that produce structured JSON output. Tasks 7-10 depend on this. If not yet implemented, add it to the Python CLI first.
- The `bridge/cli.ts` already has `show()` and `setText()` methods — no bridge changes needed for those.

**Task dependencies:** Tasks 1-5 are independent. Task 6 depends on Task 3 (reuses `removeDetailNode` helper). Tasks 7-8 are independent. Task 9 depends on Task 8. Task 10 depends on Tasks 7-9. Task 11 is independent.

---

### Task 1: Stereotype Extensibility

Replace hardcoded stereotype dropdowns with free-text inputs that accept any value.

**Files:**
- Modify: `obsidian-plugin/src/ghost/modals.ts`

- [ ] **Step 1: Replace stereotype dropdown in ProposeModal with text+datalist**

In `obsidian-plugin/src/ghost/modals.ts`, replace lines 52-59 (the stereotype dropdown in `ProposeModal`):

```typescript
    // OLD: dropdown
    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional: protocol, abstract, dataclass, enum")
      .addDropdown((drop) => {
        drop.addOption("", "(none)");
        for (const s of STEREOTYPES.filter(Boolean)) drop.addOption(s, s);
        drop.onChange((v) => { this.stereotype = v; });
      });
```

With:

```typescript
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
```

- [ ] **Step 2: Replace stereotype dropdown in CreateElementModal**

In the same file, replace lines 445-452 (the stereotype dropdown in `CreateElementModal`):

```typescript
    // OLD: dropdown
    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional: protocol, abstract, dataclass, enum")
      .addDropdown((drop) => {
        drop.addOption("", "(none)");
        for (const s of STEREOTYPES.filter(Boolean)) drop.addOption(s, s);
        drop.onChange((v) => { this.stereotype = v; });
      });
```

With:

```typescript
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
```

- [ ] **Step 3: Replace stereotype dropdown in ElevateModal**

In the same file, replace lines 255-261 (the stereotype dropdown in `ElevateModal`):

```typescript
    // OLD: dropdown
    new Setting(contentEl)
      .setName("Stereotype")
      .setDesc("Optional")
      .addDropdown((drop) => {
        drop.addOption("", "(none)");
        for (const s of STEREOTYPES.filter(Boolean)) drop.addOption(s, s);
        drop.onChange((v) => { this.stereotype = v; });
      });
```

With:

```typescript
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
```

- [ ] **Step 4: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/ghost/modals.ts
git commit -m "feat(obsidian): replace stereotype dropdowns with free-text inputs

Open set per spec — unknown stereotypes must not be rejected.
Adds datalist for autocomplete suggestions of common values."
```

---

### Task 2: Module Kind Direct Creation

Add `add-module` command and background context menu entry.

**Files:**
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Add the add-module command**

In `obsidian-plugin/src/main.ts`, add after the `add-package` command block (after line 217):

```typescript
    this.addCommand({
      id: "cooperative-coding:add-module",
      name: "Add module",
      callback: () => this.openCreateElementModal("module"),
    });
```

- [ ] **Step 2: Add module to background context menu**

In the `registerCanvasMenus` method, in the canvas background menu section, add after the "Add package..." item (after line 337):

```typescript
        menu.addItem((item: any) =>
          item.setTitle("Add module...").setIcon("file-code")
            .onClick(() => this.openCreateElementModal("module")),
        );
```

- [ ] **Step 3: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/main.ts
git commit -m "feat(obsidian): add module direct creation command and menu entry"
```

---

### Task 3: Detail Node Demotion

Add "Remove detail node" context menu option for method/field nodes.

**Files:**
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Add the removeDetailNode helper method**

In `obsidian-plugin/src/main.ts`, add as a new private method in the class (before the `// ─── List Proposals / Diff` section):

```typescript
  /**
   * Remove a detail node (method/field) and its detail edge from the canvas.
   * The code-side method/field is untouched per spec.
   */
  private removeDetailNode(nodeId: string): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;
    const data = canvas.getData?.();
    if (!data) return;

    // Remove edges connected to this node
    data.edges = (data.edges || []).filter(
      (e: any) => e.fromNode !== nodeId && e.toNode !== nodeId,
    );

    // Remove the node
    data.nodes = (data.nodes || []).filter((n: any) => n.id !== nodeId);

    canvas.setData?.(data);
    canvas.requestSave?.();

    new Notice("Detail node removed from canvas.", 3000);
    this.refreshCanvas();
  }
```

- [ ] **Step 2: Add context menu entry for detail nodes**

In the node context menu handler, inside the `if (meta)` block, add after the "Add relation..." and "Propose edge (CLI)..." items (before the closing of the `if (meta)` block, around line 282):

```typescript
          // Detail node demotion (method/field only)
          if (meta.kind === "method" || meta.kind === "field") {
            menu.addItem((item: any) =>
              item.setTitle("Remove detail node").setIcon("trash-2")
                .onClick(() => {
                  // Confirmation via simple approach - just do it, it's reversible with undo
                  this.removeDetailNode(node.id);
                }),
            );
          }
```

- [ ] **Step 3: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/main.ts
git commit -m "feat(obsidian): add detail node demotion via context menu

Right-click method/field detail nodes to remove them from canvas.
Code-side construct is untouched per spec."
```

---

### Task 4: Language Binding Selection

Add default language to settings and per-node language override to creation modals.

**Files:**
- Modify: `obsidian-plugin/src/types.ts`
- Modify: `obsidian-plugin/src/settings.ts`
- Modify: `obsidian-plugin/src/ghost/modals.ts`
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Add defaultLanguage to PluginSettings**

In `obsidian-plugin/src/types.ts`, add `defaultLanguage` to the `PluginSettings` interface and `DEFAULT_SETTINGS`:

```typescript
export interface PluginSettings {
  ccodingPath: string;
  projectRoot: string;
  showRejectedNodes: boolean;
  autoReloadOnChange: boolean;
  commandTimeout: number;
  defaultLanguage: string;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  ccodingPath: "",
  projectRoot: "",
  showRejectedNodes: false,
  autoReloadOnChange: true,
  commandTimeout: 30000,
  defaultLanguage: "",
};
```

- [ ] **Step 2: Add default language setting to settings tab**

In `obsidian-plugin/src/settings.ts`, add after the "Command timeout" setting (before the closing `}` of `display()`):

```typescript
    new Setting(containerEl)
      .setName("Default language")
      .setDesc(
        "Default programming language for canvas nodes (e.g., python, typescript). Leave empty to not set.",
      )
      .addText((text) =>
        text
          .setPlaceholder("python")
          .setValue(this.plugin.settings.defaultLanguage)
          .onChange(async (value) => {
            this.plugin.settings.defaultLanguage = value.trim();
            await this.plugin.saveSettings();
          }),
      );
```

- [ ] **Step 3: Add language field to CreateElementModal**

In `obsidian-plugin/src/ghost/modals.ts`, in the `CreateElementModal` class:

1. Add a private field: `private language = "";` (next to the other private fields)

2. Add a language input after the stereotype field in `onOpen()`:

```typescript
    new Setting(contentEl)
      .setName("Language")
      .setDesc("Optional — overrides default language for this node")
      .addText((text) =>
        text.setPlaceholder("e.g., python, typescript")
          .onChange((v) => { this.language = v; }),
      );
```

3. Update the `CreateElementResult` interface to include `language`:

```typescript
export interface CreateElementResult {
  kind: string;
  name: string;
  stereotype?: string;
  description?: string;
  language?: string;
}
```

4. Include language in the `submit()` method's result:

```typescript
    this.onDone?.({
      kind: this.kind,
      name: this.name.trim(),
      stereotype: this.stereotype || undefined,
      description: this.description.trim() || undefined,
      language: this.language.trim() || undefined,
    });
```

- [ ] **Step 4: Add language field to ProposeModal**

In the `ProposeModal` class:

1. Add a private field: `private language = "";`

2. Add a language input after the stereotype field in `onOpen()`:

```typescript
    new Setting(contentEl)
      .setName("Language")
      .setDesc("Optional — overrides default language for this node")
      .addText((text) =>
        text.setPlaceholder("e.g., python, typescript")
          .onChange((v) => { this.language = v; }),
      );
```

3. Include language in the `submit()` method, passing it through ProposeOptions. Update the interface in `bridge/cli.ts`:

In `obsidian-plugin/src/bridge/cli.ts`, add `language` to `ProposeOptions`:

```typescript
export interface ProposeOptions {
  kind: string;
  name: string;
  stereotype?: string;
  rationale?: string;
  language?: string;
}
```

And in the `propose()` method, pass it:

```typescript
  propose(opts: ProposeOptions): Promise<CommandResult> {
    const args = ["propose", "--kind", opts.kind, "--name", opts.name];
    if (opts.stereotype) args.push("--stereotype", opts.stereotype);
    if (opts.rationale) args.push("--rationale", opts.rationale);
    if (opts.language) args.push("--language", opts.language);
    return this.run(args);
  }
```

And in `ProposeModal.submit()`:

```typescript
    if (this.language.trim()) opts.language = this.language.trim();
```

- [ ] **Step 5: Pass language to createElementOnCanvas in main.ts**

In `obsidian-plugin/src/main.ts`, update `createElementOnCanvas` to set `ccoding.language` on the node. In `addNodeToCanvasData` call, the language can be set via the node metadata. However, `NewNodeData` doesn't have a `language` field.

Add `language` to `NewNodeData` in `canvas-helpers.ts`:

```typescript
export interface NewNodeData {
  kind: string;
  qualifiedName: string;
  status: string;
  stereotype?: string;
  language?: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
}
```

And in `addNodeToCanvasData`, include it in the ccoding object:

```typescript
    ccoding: {
      kind: node.kind,
      qualifiedName: node.qualifiedName,
      status: node.status,
      ...(node.stereotype ? { stereotype: node.stereotype } : {}),
      ...(node.language ? { language: node.language } : {}),
      proposedBy: null,
      proposalRationale: null,
    },
```

Then in `main.ts`, pass `language` from the `CreateElementResult`:

```typescript
  private createElementOnCanvas(element: CreateElementResult): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;
    const data = canvas.getData?.();
    if (!data) return;

    const text = buildNodeText(element.kind, element.name, element.description);
    const dims = defaultDimensions(element.kind);
    const offset = Math.floor(Math.random() * 200) - 100;

    // Use element-specific language or fall back to settings default
    const language = element.language || this.settings.defaultLanguage || undefined;

    addNodeToCanvasData(data, {
      kind: element.kind,
      qualifiedName: element.name,
      status: "accepted",
      stereotype: element.stereotype,
      language,
      text,
      x: offset,
      y: offset,
      width: dims.width,
      height: dims.height,
    });

    canvas.setData?.(data);
    canvas.requestSave?.();

    new Notice(`Created ${element.kind}: ${element.name}`, 3000);
    this.refreshCanvas();
  }
```

- [ ] **Step 6: Write canvas-level language to .canvas file**

In `obsidian-plugin/src/main.ts`, add a method to write the language to the canvas file's top-level `ccoding` metadata. This reads the raw `.canvas` JSON via the vault adapter (since `getData()`/`setData()` don't expose top-level custom fields):

```typescript
  /** Write the default language to the active canvas file's top-level ccoding metadata. */
  private async writeCanvasLanguage(language: string): Promise<void> {
    const leaf = this.app.workspace.getMostRecentLeaf();
    if (!leaf) return;
    const view = leaf.view as any;
    const filePath = view?.file?.path;
    if (!filePath || !filePath.endsWith(".canvas")) return;

    const file = this.app.vault.getAbstractFileByPath(filePath);
    if (!file) return;

    try {
      const raw = await this.app.vault.read(file as any);
      const json = JSON.parse(raw);
      json.ccoding = json.ccoding || {};
      json.ccoding.language = language || undefined;
      await this.app.vault.modify(file as any, JSON.stringify(json, null, 2));
    } catch {
      // Silently fail — non-critical operation
    }
  }
```

In `saveSettings()`, call it when the language changes:

```typescript
  async saveSettings() {
    await this.saveData(this.settings);
    this.bridge?.updateSettings(this.settings);
    this.patcher?.updateSettings(this.settings);
    // Write language to active canvas if set
    if (this.settings.defaultLanguage) {
      this.writeCanvasLanguage(this.settings.defaultLanguage);
    }
  }
```

- [ ] **Step 7: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 8: Run existing tests**

Run: `cd obsidian-plugin && npx vitest run`
Expected: All existing tests still pass.

- [ ] **Step 9: Commit**

```bash
git add obsidian-plugin/src/types.ts obsidian-plugin/src/settings.ts obsidian-plugin/src/ghost/modals.ts obsidian-plugin/src/main.ts obsidian-plugin/src/bridge/cli.ts obsidian-plugin/src/canvas-helpers.ts
git commit -m "feat(obsidian): add language binding selection

Per-canvas default language in settings (written to canvas file metadata),
per-node language override in create and propose modals."
```

---

### Task 5: Context Edge Creation

Add ConnectContextModal and context menu entries for creating context edges.

**Files:**
- Modify: `obsidian-plugin/src/ghost/modals.ts`
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Add ConnectContextResult interface and ConnectContextModal**

At the bottom of `obsidian-plugin/src/ghost/modals.ts`, add:

```typescript
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
```

- [ ] **Step 2: Add import and helper methods in main.ts**

In `obsidian-plugin/src/main.ts`, add `ConnectContextModal` and `ConnectContextResult` to the imports from `./ghost/modals`:

```typescript
import {
  ProposeModal,
  ProposeEdgeModal,
  ElevateModal,
  AddChildModal,
  CreateElementModal,
  AddRelationModal,
  ConnectContextModal,
  type AddChildResult,
  type CreateElementResult,
  type AddRelationResult,
  type ConnectContextResult,
} from "./ghost/modals";
```

Add two helper methods to the plugin class:

```typescript
  /** Get all plain (non-ccoding) nodes for context edge targeting. */
  private getPlainNodes(): Array<{ id: string; label: string }> {
    const canvas = this.currentCanvas;
    if (!canvas?.nodes) return [];
    const targets: Array<{ id: string; label: string }> = [];
    for (const [, n] of canvas.nodes) {
      const meta = parseCcodingMetadata(n.unknownData?.ccoding);
      if (meta) continue; // Skip ccoding nodes
      const label = n.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim() || n.id;
      targets.push({ id: n.id, label });
    }
    return targets;
  }

  private openConnectContextModal(sourceNode: any, sourceIsCcoding: boolean): void {
    const sourceLabel = sourceIsCcoding
      ? this.getNodeLabel(sourceNode)
      : (sourceNode.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim() || sourceNode.id);

    // If source is ccoding, targets are plain nodes. If source is plain, targets are ccoding nodes.
    const targets = sourceIsCcoding ? this.getPlainNodes() : this.getCcodingTargets();

    new ConnectContextModal(this.app, sourceLabel, sourceNode.id, targets, (result: ConnectContextResult) => {
      const canvas = this.currentCanvas;
      if (!canvas) return;
      const data = canvas.getData?.();
      if (!data) return;

      addEdgeToCanvasData(data, {
        fromNode: sourceNode.id,
        toNode: result.targetId,
        relation: "context",
        status: "accepted",
        label: result.label,
      });

      canvas.setData?.(data);
      canvas.requestSave?.();

      new Notice("Context link created", 3000);
      this.refreshCanvas();
    }).open();
  }
```

- [ ] **Step 3: Add context menu entry for ccoding nodes**

In the node context menu handler, inside the `if (meta)` block, add after the "Propose edge (CLI)..." item:

```typescript
          // Context edge creation
          menu.addItem((item: any) =>
            item.setTitle("Attach context note...").setIcon("file-text")
              .onClick(() => this.openConnectContextModal(node, true)),
          );
```

- [ ] **Step 4: Add context menu entry for plain nodes**

In the `else` block of the node context menu (where plain nodes get "Elevate to ccoding element"), add before the elevate option:

```typescript
          menu.addItem((item: any) =>
            item.setTitle("Connect to code element...").setIcon("link")
              .onClick(() => this.openConnectContextModal(node, false)),
          );
```

- [ ] **Step 5: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 6: Run existing tests**

Run: `cd obsidian-plugin && npx vitest run`
Expected: All tests pass (context highlighter tests still work — they only test highlighting, not creation).

- [ ] **Step 7: Commit**

```bash
git add obsidian-plugin/src/ghost/modals.ts obsidian-plugin/src/main.ts
git commit -m "feat(obsidian): add context edge creation UI

ConnectContextModal lets users link plain canvas notes to code elements
via context edges. Available from both plain node and ccoding node
context menus."
```

---

### Task 6: Stale Node Recovery Modal

**Depends on:** Task 3 (reuses `removeDetailNode` helper for the "remove" option).

Replace the direct restore action with a modal offering three recovery options.

**Files:**
- Create: `obsidian-plugin/src/ghost/restore-modal.ts`
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Create RestoreModal**

Create `obsidian-plugin/src/ghost/restore-modal.ts`:

```typescript
// src/ghost/restore-modal.ts
import { Modal, Setting, App, Notice } from "obsidian";
import type { CcodingBridge } from "../bridge/cli";

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
```

- [ ] **Step 2: Wire RestoreModal into main.ts**

In `obsidian-plugin/src/main.ts`, add the import:

```typescript
import { RestoreModal, type RestoreChoice } from "./ghost/restore-modal";
```

Add a handler method:

```typescript
  private openRestoreModal(node: any): void {
    const meta = parseCcodingMetadata(node?.unknownData?.ccoding);
    if (!meta) return;

    const qualifiedName = meta.qualifiedName || "unknown";
    const sourcePath = meta.source || "";

    new RestoreModal(this.app, node.id, qualifiedName, sourcePath, async (choice: RestoreChoice) => {
      if (choice.action === "restore") {
        await this.runAction(() => restoreElement(this.bridge, node.id));
      } else if (choice.action === "relink") {
        // Update canvas data directly, then sync
        const canvas = this.currentCanvas;
        if (!canvas) return;
        const data = canvas.getData?.();
        if (!data) return;

        const canvasNode = data.nodes.find((n: any) => n.id === node.id);
        if (canvasNode?.ccoding) {
          canvasNode.ccoding.qualifiedName = choice.qualifiedName;
          canvasNode.ccoding.source = choice.source;
          canvasNode.ccoding.status = "accepted";
        }
        canvas.setData?.(data);
        canvas.requestSave?.();
        new Notice(`Re-linked to ${choice.qualifiedName}`, 3000);
        this.refreshCanvas();
        // Sync to propagate the re-link
        await this.runAction(() => syncCanvas(this.bridge));
      } else if (choice.action === "remove") {
        this.removeDetailNode(node.id); // Reuses the same removal logic
      }
    }).open();
  }
```

- [ ] **Step 3: Replace direct restore call with modal in context menu**

In the stale node context menu section (around line 247-253), replace:

```typescript
            } else if (meta.status === "stale") {
              menu.addSeparator();
              menu.addItem((item: any) =>
                item.setTitle("Restore (re-link to code)").setIcon("refresh-cw")
                  .onClick(() => this.runAction(() => restoreElement(this.bridge, node.id))),
              );
            }
```

With:

```typescript
            } else if (meta.status === "stale") {
              menu.addSeparator();
              menu.addItem((item: any) =>
                item.setTitle("Recover stale element...").setIcon("refresh-cw")
                  .onClick(() => this.openRestoreModal(node)),
              );
            }
```

- [ ] **Step 4: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/ghost/restore-modal.ts obsidian-plugin/src/main.ts
git commit -m "feat(obsidian): add stale node recovery modal

Replace direct restore with 3-option modal: restore code, re-link
to different element, or remove from canvas."
```

---

### Task 7: Sync Output Parser

Create a testable parser for structured sync/status CLI output.

**Files:**
- Create: `obsidian-plugin/src/sync/output-parser.ts`
- Create: `obsidian-plugin/tests/sync/output-parser.test.ts`

- [ ] **Step 1: Write failing tests**

Create `obsidian-plugin/tests/sync/output-parser.test.ts`:

```typescript
// tests/sync/output-parser.test.ts
import { describe, it, expect } from "vitest";
import { parseSyncOutput, type SyncSummary } from "../../src/sync/output-parser";

describe("parseSyncOutput", () => {
  it("parses successful sync with changes", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({
        status: "ok",
        synced: [
          { qualifiedName: "UserService", action: "updated" },
          { qualifiedName: "AuthController", action: "created" },
        ],
        conflicts: [],
      }),
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.nodesUpdated).toBe(1);
    expect(summary.nodesCreated).toBe(1);
    expect(summary.conflicts).toBe(0);
    expect(summary.ok).toBe(true);
  });

  it("parses sync with conflicts", () => {
    const result = {
      success: false,
      stdout: JSON.stringify({
        status: "conflicts",
        synced: [],
        conflicts: [
          {
            qualifiedName: "UserService",
            elementKind: "class",
            elementId: "abc123",
            canvasSummary: "Added method parse()",
            codeSummary: "Changed method signature",
          },
        ],
      }),
      stderr: "",
      exitCode: 1,
    };

    const summary = parseSyncOutput(result);
    expect(summary.conflicts).toBe(1);
    expect(summary.ok).toBe(false);
  });

  it("returns raw fallback for non-JSON output", () => {
    const result = {
      success: true,
      stdout: "Already in sync.",
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.ok).toBe(true);
    expect(summary.rawOutput).toBe("Already in sync.");
  });

  it("handles empty stdout", () => {
    const result = {
      success: true,
      stdout: "",
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.ok).toBe(true);
  });

  it("formats a human-readable summary", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({
        status: "ok",
        synced: [
          { qualifiedName: "A", action: "updated" },
          { qualifiedName: "B", action: "updated" },
          { qualifiedName: "C", action: "created" },
        ],
        conflicts: [],
      }),
      stderr: "",
      exitCode: 0,
    };

    const summary = parseSyncOutput(result);
    expect(summary.displayText).toContain("2 updated");
    expect(summary.displayText).toContain("1 created");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npx vitest run tests/sync/output-parser.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the parser**

Create `obsidian-plugin/src/sync/output-parser.ts`:

```typescript
// src/sync/output-parser.ts
import type { CommandResult } from "../types";

export interface SyncSummary {
  ok: boolean;
  nodesUpdated: number;
  nodesCreated: number;
  edgesUpdated: number;
  conflicts: number;
  rawOutput: string;
  displayText: string;
}

interface SyncJsonOutput {
  status: string;
  synced: Array<{ qualifiedName: string; action: string }>;
  conflicts: Array<unknown>;
}

/**
 * Parse the CLI sync/status output into a structured summary.
 * Expects JSON from `ccoding sync --json`. Falls back gracefully
 * for non-JSON output.
 */
export function parseSyncOutput(result: CommandResult): SyncSummary {
  const raw = result.stdout.trim();

  try {
    const json: SyncJsonOutput = JSON.parse(raw);

    const updated = json.synced.filter((s) => s.action === "updated").length;
    const created = json.synced.filter((s) => s.action === "created").length;
    const edgesUpdated = json.synced.filter((s) => s.action === "edge_updated").length;
    const conflicts = json.conflicts?.length ?? 0;

    const parts: string[] = [];
    if (updated > 0) parts.push(`${updated} updated`);
    if (created > 0) parts.push(`${created} created`);
    if (edgesUpdated > 0) parts.push(`${edgesUpdated} edges updated`);
    if (conflicts > 0) parts.push(`${conflicts} conflict${conflicts !== 1 ? "s" : ""}`);

    const displayText = parts.length > 0
      ? `Sync complete: ${parts.join(", ")}`
      : "Sync complete: no changes";

    return {
      ok: json.status !== "conflicts",
      nodesUpdated: updated,
      nodesCreated: created,
      edgesUpdated,
      conflicts,
      rawOutput: raw,
      displayText,
    };
  } catch {
    // Non-JSON output — fall back to raw text
    return {
      ok: result.success,
      nodesUpdated: 0,
      nodesCreated: 0,
      edgesUpdated: 0,
      conflicts: 0,
      rawOutput: raw,
      displayText: raw || "Sync complete",
    };
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npx vitest run tests/sync/output-parser.test.ts`
Expected: All 5 tests PASS.

- [ ] **Step 5: Run all tests**

Run: `cd obsidian-plugin && npx vitest run`
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add obsidian-plugin/src/sync/output-parser.ts obsidian-plugin/tests/sync/output-parser.test.ts
git commit -m "feat(obsidian): add sync output parser

Parses ccoding sync --json output into structured SyncSummary.
Falls back gracefully for non-JSON output."
```

---

### Task 8: Conflict Parser

Create a testable parser for extracting conflict info from sync JSON output.

**Files:**
- Create: `obsidian-plugin/src/sync/conflict-parser.ts`
- Create: `obsidian-plugin/tests/sync/conflict-parser.test.ts`

- [ ] **Step 1: Write failing tests**

Create `obsidian-plugin/tests/sync/conflict-parser.test.ts`:

```typescript
// tests/sync/conflict-parser.test.ts
import { describe, it, expect } from "vitest";
import { parseConflictOutput, type ConflictInfo } from "../../src/sync/conflict-parser";

describe("parseConflictOutput", () => {
  it("extracts conflicts from JSON output", () => {
    const result = {
      success: false,
      stdout: JSON.stringify({
        status: "conflicts",
        synced: [],
        conflicts: [
          {
            qualifiedName: "UserService",
            elementKind: "class",
            elementId: "abc123",
            canvasSummary: "Added method parse()",
            codeSummary: "Changed method signature of process()",
          },
          {
            qualifiedName: "AuthController",
            elementKind: "class",
            elementId: "def456",
            canvasSummary: "Renamed to LoginController",
            codeSummary: "Added new dependency",
          },
        ],
      }),
      stderr: "",
      exitCode: 1,
    };

    const conflicts = parseConflictOutput(result);
    expect(conflicts).toHaveLength(2);
    expect(conflicts[0].qualifiedName).toBe("UserService");
    expect(conflicts[0].elementKind).toBe("class");
    expect(conflicts[0].elementId).toBe("abc123");
    expect(conflicts[0].canvasSummary).toBe("Added method parse()");
    expect(conflicts[0].codeSummary).toBe("Changed method signature of process()");
  });

  it("returns empty array for non-JSON output", () => {
    const result = {
      success: false,
      stdout: "Error: something went wrong",
      stderr: "",
      exitCode: 1,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });

  it("returns empty array for successful sync with no conflicts", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({ status: "ok", synced: [], conflicts: [] }),
      stderr: "",
      exitCode: 0,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });

  it("returns empty array when conflicts field is missing", () => {
    const result = {
      success: true,
      stdout: JSON.stringify({ status: "ok", synced: [] }),
      stderr: "",
      exitCode: 0,
    };
    expect(parseConflictOutput(result)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npx vitest run tests/sync/conflict-parser.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the parser**

Create `obsidian-plugin/src/sync/conflict-parser.ts`:

```typescript
// src/sync/conflict-parser.ts
import type { CommandResult } from "../types";

export interface ConflictInfo {
  qualifiedName: string;
  elementKind: string;
  elementId: string;
  canvasSummary: string;
  codeSummary: string;
}

/**
 * Parse conflict information from `ccoding sync --json` output.
 * Returns an empty array if the output is not JSON or has no conflicts.
 */
export function parseConflictOutput(result: CommandResult): ConflictInfo[] {
  try {
    const json = JSON.parse(result.stdout.trim());
    const conflicts = json.conflicts;
    if (!Array.isArray(conflicts)) return [];

    return conflicts.map((c: any) => ({
      qualifiedName: String(c.qualifiedName ?? ""),
      elementKind: String(c.elementKind ?? ""),
      elementId: String(c.elementId ?? ""),
      canvasSummary: String(c.canvasSummary ?? ""),
      codeSummary: String(c.codeSummary ?? ""),
    }));
  } catch {
    return [];
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npx vitest run tests/sync/conflict-parser.test.ts`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/sync/conflict-parser.ts obsidian-plugin/tests/sync/conflict-parser.test.ts
git commit -m "feat(obsidian): add conflict parser for sync JSON output

Extracts per-element conflict info from ccoding sync --json output."
```

---

### Task 9: Conflict Resolution Modal

Create the modal that presents conflicts and collects resolution choices.

**Files:**
- Create: `obsidian-plugin/src/sync/conflict-modal.ts`

- [ ] **Step 1: Create ConflictResolutionModal**

Create `obsidian-plugin/src/sync/conflict-modal.ts`:

```typescript
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
```

- [ ] **Step 2: Build and verify**

Run: `cd obsidian-plugin && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add obsidian-plugin/src/sync/conflict-modal.ts
git commit -m "feat(obsidian): add conflict resolution modal

Shows per-element conflict details with Keep Canvas / Keep Code / Skip
buttons. Returns resolution choices to caller."
```

---

### Task 10: Sync & Conflict Integration

Wire the parsers and conflict modal into the sync action flow.

**Files:**
- Modify: `obsidian-plugin/src/ghost/actions.ts`
- Modify: `obsidian-plugin/src/bridge/cli.ts`
- Modify: `obsidian-plugin/tests/ghost/actions.test.ts`

- [ ] **Step 1: Add syncJson method to bridge**

In `obsidian-plugin/src/bridge/cli.ts`, add:

```typescript
  /** Sync with JSON output for structured parsing. */
  syncJson(): Promise<CommandResult> {
    return this.run(["sync", "--json"]);
  }

  /** Status with JSON output for structured parsing. */
  statusJson(): Promise<CommandResult> {
    return this.run(["status", "--json"]);
  }
```

- [ ] **Step 2: Rewrite syncCanvas to use parser and conflict modal**

In `obsidian-plugin/src/ghost/actions.ts`, replace the existing `syncCanvas` function and add the new imports:

```typescript
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
```

Replace the `syncCanvas` function:

```typescript
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
    // Note: spec says notices should be clickable to show raw output.
    // Obsidian's Notice API doesn't natively support click handlers.
    // Deferred — can be added later with custom DOM manipulation on notice.noticeEl.
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
```

Also rewrite `checkStatus` to use structured output with error handling:

```typescript
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
```

- [ ] **Step 3: Update main.ts to pass app to syncCanvas**

In `obsidian-plugin/src/main.ts`, update the sync command and runAction calls to pass `this.app`:

For the sync command (around line 141):

```typescript
        if (!checking) this.runAction(() => syncCanvas(this.bridge, this.app));
```

And in the `openRestoreModal` method (if created in Task 6), update the sync call there too:

```typescript
        await this.runAction(() => syncCanvas(this.bridge, this.app));
```

- [ ] **Step 4: Update the test mock for syncJson**

In `obsidian-plugin/tests/ghost/actions.test.ts`, update the mock bridge to include `syncJson`:

```typescript
function mockBridge(result: any): CcodingBridge {
  return {
    accept: vi.fn().mockResolvedValue(result),
    reject: vi.fn().mockResolvedValue(result),
    reconsider: vi.fn().mockResolvedValue(result),
    acceptAll: vi.fn().mockResolvedValue(result),
    rejectAll: vi.fn().mockResolvedValue(result),
    sync: vi.fn().mockResolvedValue(result),
    syncJson: vi.fn().mockResolvedValue(result),
    status: vi.fn().mockResolvedValue(result),
    statusJson: vi.fn().mockResolvedValue(result),
    show: vi.fn().mockResolvedValue(result),
    setText: vi.fn().mockResolvedValue(result),
  } as any;
}
```

Update the retry test to use `syncJson`:

```typescript
  it("retries on busy error", async () => {
    const busyResult = { success: false, stdout: "", stderr: "EBUSY: file locked", exitCode: 1 };
    const okResult = { success: true, stdout: JSON.stringify({ status: "ok", synced: [], conflicts: [] }), stderr: "", exitCode: 0 };
    const bridge = mockBridge(busyResult);
    (bridge.syncJson as any)
      .mockResolvedValueOnce(busyResult)
      .mockResolvedValueOnce(okResult);
    await syncCanvas(bridge);
    expect(bridge.syncJson).toHaveBeenCalledTimes(2);
  });
```

Note: The `syncCanvas` function signature changed to accept an optional `app` parameter. The test calls it without `app`, which means conflicts won't open a modal (just fall through). This is correct for unit testing.

- [ ] **Step 5: Build and run all tests**

Run: `cd obsidian-plugin && npm run build && npx vitest run`
Expected: Build succeeds, all tests pass.

- [ ] **Step 6: Commit**

```bash
git add obsidian-plugin/src/ghost/actions.ts obsidian-plugin/src/bridge/cli.ts obsidian-plugin/src/main.ts obsidian-plugin/tests/ghost/actions.test.ts
git commit -m "feat(obsidian): integrate sync output parser and conflict resolution

Sync now uses --json flag, shows structured notices, and opens
conflict resolution modal when conflicts are detected."
```

---

### Task 11: Bulk Operations Modal

Create the modal for selective accept/reject of proposals.

**Files:**
- Create: `obsidian-plugin/src/ghost/bulk-modal.ts`
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Create BulkOperationsModal**

Create `obsidian-plugin/src/ghost/bulk-modal.ts`:

```typescript
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
```

- [ ] **Step 2: Wire BulkOperationsModal into main.ts**

In `obsidian-plugin/src/main.ts`, add the import:

```typescript
import { BulkOperationsModal } from "./ghost/bulk-modal";
```

Add the command in `registerCommands()`:

```typescript
    this.addCommand({
      id: "cooperative-coding:bulk-manage",
      name: "Manage proposals...",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) {
          const canvas = this.currentCanvas;
          if (!canvas) return;
          const data = canvas.getData?.();
          if (!data) return;
          new BulkOperationsModal(this.app, data, this.bridge, () => this.refreshCanvas()).open();
        }
        return true;
      },
    });
```

Add the background context menu entry in `registerCanvasMenus()`, in the CLI-backed proposals section:

```typescript
          menu.addItem((item: any) =>
            item.setTitle("Manage proposals...").setIcon("list-checks")
              .onClick(() => {
                const canvas = this.currentCanvas;
                if (!canvas) return;
                const data = canvas.getData?.();
                if (!data) return;
                new BulkOperationsModal(this.app, data, this.bridge, () => this.refreshCanvas()).open();
              }),
          );
```

- [ ] **Step 3: Build and run all tests**

Run: `cd obsidian-plugin && npm run build && npx vitest run`
Expected: Build succeeds, all tests pass.

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/ghost/bulk-modal.ts obsidian-plugin/src/main.ts
git commit -m "feat(obsidian): add selective bulk operations modal

Filterable list of proposals with per-item accept/reject selection.
Supports kind and text filtering."
```

---

## Summary

| Task | Feature | New Files | Modified Files |
|------|---------|-----------|----------------|
| 1 | Stereotype extensibility | — | `ghost/modals.ts` |
| 2 | Module direct creation | — | `main.ts` |
| 3 | Detail node demotion | — | `main.ts` |
| 4 | Language binding selection | — | `types.ts`, `settings.ts`, `ghost/modals.ts`, `main.ts`, `bridge/cli.ts`, `canvas-helpers.ts` |
| 5 | Context edge creation | — | `ghost/modals.ts`, `main.ts` |
| 6 | Stale node recovery | `ghost/restore-modal.ts` | `main.ts` |
| 7 | Sync output parser | `sync/output-parser.ts`, `tests/sync/output-parser.test.ts` | — |
| 8 | Conflict parser | `sync/conflict-parser.ts`, `tests/sync/conflict-parser.test.ts` | — |
| 9 | Conflict resolution modal | `sync/conflict-modal.ts` | — |
| 10 | Sync & conflict integration | — | `ghost/actions.ts`, `bridge/cli.ts`, `main.ts`, `tests/ghost/actions.test.ts` |
| 11 | Bulk operations modal | `ghost/bulk-modal.ts` | `main.ts` |

**Total:** 5 new source files, 2 new test files, 8 modified files.
