// src/main.ts
import { Plugin, Notice } from "obsidian";
import { type PluginSettings, DEFAULT_SETTINGS, parseCcodingMetadata, parseEdgeMetadata } from "./types";
import { CcodingSettingTab } from "./settings";
import { CcodingBridge } from "./bridge/cli";
import { CanvasWatcher } from "./watcher/canvas-watcher";
import { CanvasPatcher } from "./canvas-patcher";
import { ContextHighlighter } from "./highlight/context";
import {
  acceptElement,
  rejectElement,
  reconsiderElement,
  restoreElement,
  acceptAll,
  rejectAll,
  syncCanvas,
  checkStatus,
} from "./ghost/actions";
import {
  ProposeModal,
  ProposeEdgeModal,
  ElevateModal,
  AddChildModal,
  CreateElementModal,
  AddRelationModal,
  type AddChildResult,
  type CreateElementResult,
  type AddRelationResult,
} from "./ghost/modals";
import { layoutCanvas } from "./layout/hierarchical";
import {
  addNodeToCanvasData,
  addEdgeToCanvasData,
  computeChildPosition,
  defaultDimensions,
  buildNodeText,
} from "./canvas-helpers";

export default class CooperativeCodingPlugin extends Plugin {
  settings: PluginSettings = DEFAULT_SETTINGS;
  bridge!: CcodingBridge;
  watcher!: CanvasWatcher;
  patcher!: CanvasPatcher;
  highlighter!: ContextHighlighter;
  private cliAvailable = false;
  private selectionHandler: ((selection: Set<any>) => void) | null = null;
  private currentCanvas: any = null;
  private statusBarEl: HTMLElement | null = null;

  async onload() {
    await this.loadSettings();
    this.bridge = new CcodingBridge(this.settings);
    this.patcher = new CanvasPatcher(this, this.settings);
    this.highlighter = new ContextHighlighter();
    this.watcher = new CanvasWatcher(
      () => this.onCanvasFileChanged(),
      () => new Notice("Canvas file was deleted or renamed. Watcher stopped.", 5000),
    );

    // Settings tab
    this.addSettingTab(new CcodingSettingTab(this.app, this));

    // Status bar indicator
    this.statusBarEl = this.addStatusBarItem();
    this.updateStatusBar(false);

    // Set vault base path for project root auto-detection
    const basePath = (this.app.vault.adapter as any).getBasePath?.() || "";
    this.bridge.setVaultBasePath(basePath);

    // Check CLI availability (non-blocking)
    this.bridge.isAvailable().then((available) => {
      this.cliAvailable = available;
      this.updateStatusBar(available);
      if (!available) {
        new Notice(
          "ccoding CLI not found. Install it or set the path in CooperativeCoding plugin settings.",
          0,
        );
      }
    });

    this.registerCommands();
    this.registerCanvasMenus();

    // Register canvas view event
    this.registerEvent(
      this.app.workspace.on("layout-change", () => {
        this.tryAttachToCanvas();
      }),
    );

    // Try to attach to an already-open canvas
    this.tryAttachToCanvas();
  }

  onunload() {
    this.detachSelectionListener();
    this.highlighter.detach();
    this.watcher.stop();
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.bridge?.updateSettings(this.settings);
    this.patcher?.updateSettings(this.settings);
  }

  // ─── Commands ──────────────────────────────────────────────

  private registerCommands(): void {
    this.addCommand({
      id: "cooperative-coding:accept-all",
      name: "Accept all proposals",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) this.runAction(() => acceptAll(this.bridge));
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:reject-all",
      name: "Reject all proposals",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) this.runAction(() => rejectAll(this.bridge));
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:sync",
      name: "Sync canvas with code",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) this.runAction(() => syncCanvas(this.bridge));
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:status",
      name: "Check sync status",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) checkStatus(this.bridge);
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:propose",
      name: "Propose new element",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) {
          new ProposeModal(this.app, this.bridge, () => this.refreshCanvas()).open();
        }
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:list-proposals",
      name: "List pending proposals",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) this.listProposals();
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:diff",
      name: "Preview sync changes",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) this.showDiff();
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:layout",
      name: "Layout canvas",
      callback: () => this.runLayout(false),
    });

    this.addCommand({
      id: "cooperative-coding:layout-all",
      name: "Layout all nodes",
      callback: () => this.runLayout(true),
    });

    // Direct canvas commands (no CLI needed)
    this.addCommand({
      id: "cooperative-coding:add-class",
      name: "Add class",
      callback: () => this.openCreateElementModal("class"),
    });

    this.addCommand({
      id: "cooperative-coding:add-interface",
      name: "Add interface",
      callback: () => this.openCreateElementModal("interface"),
    });

    this.addCommand({
      id: "cooperative-coding:add-package",
      name: "Add package",
      callback: () => this.openCreateElementModal("package"),
    });

    this.addCommand({
      id: "cooperative-coding:add-module",
      name: "Add module",
      callback: () => this.openCreateElementModal("module"),
    });
  }

  // ─── Canvas Context Menus ──────────────────────────────────

  private registerCanvasMenus(): void {
    // Node context menu
    this.registerEvent(
      this.app.workspace.on("canvas:node-menu" as any, (menu: any, node: any) => {
        const meta = parseCcodingMetadata(node?.unknownData?.ccoding);

        if (meta) {
          // CLI-backed actions (accept/reject/reconsider)
          if (this.cliAvailable) {
            if (meta.status === "proposed") {
              menu.addSeparator();
              menu.addItem((item: any) =>
                item.setTitle("Accept proposal").setIcon("check")
                  .onClick(() => this.runAction(() => acceptElement(this.bridge, node.id))),
              );
              menu.addItem((item: any) =>
                item.setTitle("Reject proposal").setIcon("x")
                  .onClick(() => this.runAction(() => rejectElement(this.bridge, node.id))),
              );
            } else if (meta.status === "rejected") {
              menu.addSeparator();
              menu.addItem((item: any) =>
                item.setTitle("Reconsider").setIcon("rotate-ccw")
                  .onClick(() => this.runAction(() => reconsiderElement(this.bridge, node.id))),
              );
            } else if (meta.status === "stale") {
              menu.addSeparator();
              menu.addItem((item: any) =>
                item.setTitle("Restore (re-link to code)").setIcon("refresh-cw")
                  .onClick(() => this.runAction(() => restoreElement(this.bridge, node.id))),
              );
            }
          }

          // Direct canvas actions (no CLI needed)
          const isContainer = meta.kind === "class" || meta.kind === "interface";
          if (isContainer) {
            menu.addSeparator();
            menu.addItem((item: any) =>
              item.setTitle("Add field...").setIcon("text-cursor-input")
                .onClick(() => this.openAddChildModal(node, "field")),
            );
            menu.addItem((item: any) =>
              item.setTitle("Add method...").setIcon("function-square")
                .onClick(() => this.openAddChildModal(node, "method")),
            );
          }

          // Add relation (direct, no CLI)
          menu.addItem((item: any) =>
            item.setTitle("Add relation...").setIcon("git-branch")
              .onClick(() => this.openAddRelationModal(node)),
          );

          // CLI-backed propose edge
          if (this.cliAvailable) {
            menu.addItem((item: any) =>
              item.setTitle("Propose edge (CLI)...").setIcon("git-branch")
                .onClick(() => this.openProposeEdgeModal(node)),
            );
          }
        } else {
          // Plain canvas node — offer to elevate
          menu.addSeparator();
          menu.addItem((item: any) =>
            item.setTitle("Elevate to ccoding element").setIcon("arrow-up-circle")
              .onClick(() => this.openElevateModal(node)),
          );
        }
      }),
    );

    // Edge context menu
    this.registerEvent(
      this.app.workspace.on("canvas:edge-menu" as any, (menu: any, edge: any) => {
        if (!this.cliAvailable) return;
        const meta = parseEdgeMetadata(edge?.unknownData?.ccoding);
        if (!meta) return;

        if (meta.status === "proposed") {
          menu.addSeparator();
          menu.addItem((item: any) =>
            item.setTitle("Accept proposal").setIcon("check")
              .onClick(() => this.runAction(() => acceptElement(this.bridge, edge.id))),
          );
          menu.addItem((item: any) =>
            item.setTitle("Reject proposal").setIcon("x")
              .onClick(() => this.runAction(() => rejectElement(this.bridge, edge.id))),
          );
        } else if (meta.status === "rejected") {
          menu.addSeparator();
          menu.addItem((item: any) =>
            item.setTitle("Reconsider").setIcon("rotate-ccw")
              .onClick(() => this.runAction(() => reconsiderElement(this.bridge, edge.id))),
          );
        }
      }),
    );

    // Canvas background context menu
    this.registerEvent(
      this.app.workspace.on("canvas:menu" as any, (menu: any) => {
        // Direct element creation (no CLI needed)
        menu.addSeparator();
        menu.addItem((item: any) =>
          item.setTitle("Add class...").setIcon("box")
            .onClick(() => this.openCreateElementModal("class")),
        );
        menu.addItem((item: any) =>
          item.setTitle("Add interface...").setIcon("layout-template")
            .onClick(() => this.openCreateElementModal("interface")),
        );
        menu.addItem((item: any) =>
          item.setTitle("Add package...").setIcon("package")
            .onClick(() => this.openCreateElementModal("package")),
        );
        menu.addItem((item: any) =>
          item.setTitle("Add module...").setIcon("file-code")
            .onClick(() => this.openCreateElementModal("module")),
        );

        // CLI-backed proposals
        if (this.cliAvailable) {
          menu.addSeparator();
          menu.addItem((item: any) =>
            item.setTitle("Propose new class (CLI)...").setIcon("plus-circle")
              .onClick(() => {
                new ProposeModal(this.app, this.bridge, () => this.refreshCanvas(), "class").open();
              }),
          );
          menu.addItem((item: any) =>
            item.setTitle("Propose new interface (CLI)...").setIcon("plus-circle")
              .onClick(() => {
                new ProposeModal(this.app, this.bridge, () => this.refreshCanvas(), "interface").open();
              }),
          );
        }

        menu.addSeparator();
        menu.addItem((item: any) =>
          item.setTitle("Layout all nodes").setIcon("layout-grid")
            .onClick(() => this.runLayout(true)),
        );
      }),
    );
  }

  // ─── Propose Edge Modal ────────────────────────────────────

  private openProposeEdgeModal(sourceNode: any): void {
    const canvas = this.currentCanvas;
    if (!canvas?.nodes) return;

    // Build list of all ccoding nodes as potential targets
    const targets: Array<{ id: string; label: string }> = [];
    for (const [, n] of canvas.nodes) {
      const meta = parseCcodingMetadata(n.unknownData?.ccoding);
      if (!meta) continue;
      const label = meta.qualifiedName
        || n.unknownData?.ccoding?.name
        || n.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim()
        || n.id;
      targets.push({ id: n.id, label });
    }

    const sourceMeta = parseCcodingMetadata(sourceNode.unknownData?.ccoding);
    const sourceLabel = sourceMeta?.qualifiedName
      || sourceNode.unknownData?.ccoding?.name
      || sourceNode.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim()
      || sourceNode.id;

    new ProposeEdgeModal(
      this.app,
      this.bridge,
      sourceNode.id,
      sourceLabel,
      targets,
      () => this.refreshCanvas(),
    ).open();
  }

  // ─── Elevate plain node to ccoding ─────────────────────────

  private openElevateModal(node: any): void {
    const text = node.text || "";
    new ElevateModal(this.app, node.id, text, (meta) => {
      this.elevateNode(node, meta);
    }).open();
  }

  private elevateNode(
    node: any,
    meta: { kind: string; name: string; stereotype?: string },
  ): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;

    const data = canvas.getData?.();
    if (!data) return;

    // Find the node in canvas data and add ccoding metadata
    const canvasNode = data.nodes.find((n: any) => n.id === node.id);
    if (!canvasNode) return;

    canvasNode.ccoding = {
      kind: meta.kind,
      qualifiedName: meta.name,
      status: "accepted",
      ...(meta.stereotype ? { stereotype: meta.stereotype } : {}),
    };

    canvas.setData?.(data);
    canvas.requestSave?.();

    new Notice(`Elevated "${meta.name}" to ccoding ${meta.kind}`, 3000);
    this.refreshCanvas();
  }

  // ─── Direct Canvas Element Creation ────────────────────────

  private getNodeLabel(node: any): string {
    const meta = parseCcodingMetadata(node?.unknownData?.ccoding);
    return meta?.qualifiedName
      || node?.unknownData?.ccoding?.name
      || node?.text?.split("\n")[0]?.replace(/^#+\s*/, "").trim()
      || node?.id;
  }

  private getCcodingTargets(): Array<{ id: string; label: string }> {
    const canvas = this.currentCanvas;
    if (!canvas?.nodes) return [];
    const targets: Array<{ id: string; label: string }> = [];
    for (const [, n] of canvas.nodes) {
      const meta = parseCcodingMetadata(n.unknownData?.ccoding);
      if (!meta) continue;
      targets.push({ id: n.id, label: this.getNodeLabel(n) });
    }
    return targets;
  }

  private openAddChildModal(parentNode: any, kind: "field" | "method"): void {
    const parentLabel = this.getNodeLabel(parentNode);
    const parentMeta = parseCcodingMetadata(parentNode?.unknownData?.ccoding);
    const parentQualifiedName = parentMeta?.qualifiedName || parentLabel;

    new AddChildModal(this.app, parentLabel, kind, (result: AddChildResult) => {
      this.addChildToNode(parentNode.id, parentQualifiedName, result);
    }).open();
  }

  private addChildToNode(
    parentId: string,
    parentQualifiedName: string,
    child: AddChildResult,
  ): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;
    const data = canvas.getData?.();
    if (!data) return;

    // Build node text
    let text: string;
    if (child.kind === "field") {
      const typePart = child.typeName ? `\`${child.typeName}\`` : "";
      const descParts = [typePart, child.description].filter(Boolean).join(" — ");
      text = buildNodeText(child.kind, child.name, descParts || undefined);
    } else {
      // method
      const sigParts: string[] = [];
      if (child.params) sigParts.push(`**Params:** \`${child.params}\``);
      if (child.returnType) sigParts.push(`**Returns:** \`${child.returnType}\``);
      if (child.description) sigParts.push(`\n${child.description}`);
      const body = sigParts.join("\n") || undefined;
      text = buildNodeText(child.kind, `${child.name}()`, body);
    }

    const dims = defaultDimensions(child.kind);
    const pos = computeChildPosition(data, parentId, dims.width, dims.height);

    const qualifiedName = `${parentQualifiedName}.${child.name}`;

    const nodeId = addNodeToCanvasData(data, {
      kind: child.kind,
      qualifiedName,
      status: "accepted",
      text,
      x: pos.x,
      y: pos.y,
      width: dims.width,
      height: dims.height,
    });

    addEdgeToCanvasData(data, {
      fromNode: parentId,
      toNode: nodeId,
      relation: "detail",
      status: "accepted",
      fromSide: "right",
      toSide: "left",
    });

    canvas.setData?.(data);
    canvas.requestSave?.();

    new Notice(`Added ${child.kind}: ${child.name}`, 3000);
    this.refreshCanvas();
  }

  private openCreateElementModal(defaultKind?: string): void {
    new CreateElementModal(this.app, defaultKind, (result: CreateElementResult) => {
      this.createElementOnCanvas(result);
    }).open();
  }

  private createElementOnCanvas(element: CreateElementResult): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;
    const data = canvas.getData?.();
    if (!data) return;

    const text = buildNodeText(element.kind, element.name, element.description);
    const dims = defaultDimensions(element.kind);

    // Place near the center of the viewport, offset by a random small amount
    // to avoid stacking on the same spot
    const offset = Math.floor(Math.random() * 200) - 100;

    addNodeToCanvasData(data, {
      kind: element.kind,
      qualifiedName: element.name,
      status: "accepted",
      stereotype: element.stereotype,
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

  private openAddRelationModal(sourceNode: any): void {
    const sourceLabel = this.getNodeLabel(sourceNode);
    const targets = this.getCcodingTargets();

    new AddRelationModal(this.app, sourceLabel, sourceNode.id, targets, (result: AddRelationResult) => {
      this.addRelationToCanvas(sourceNode.id, result);
    }).open();
  }

  private addRelationToCanvas(sourceId: string, relation: AddRelationResult): void {
    const canvas = this.currentCanvas;
    if (!canvas) return;
    const data = canvas.getData?.();
    if (!data) return;

    addEdgeToCanvasData(data, {
      fromNode: sourceId,
      toNode: relation.targetId,
      relation: relation.relation,
      status: "accepted",
      label: relation.label,
    });

    canvas.setData?.(data);
    canvas.requestSave?.();

    new Notice(`Added ${relation.relation} relation`, 3000);
    this.refreshCanvas();
  }

  // ─── List Proposals / Diff ─────────────────────────────────

  private async listProposals(): Promise<void> {
    const result = await this.bridge.ghosts();
    if (result.success) {
      const text = result.stdout.trim() || "No pending proposals.";
      new Notice(text, text.length > 100 ? 15000 : 5000);
    } else {
      new Notice(`Error: ${result.stderr}`, 5000);
    }
  }

  private async showDiff(): Promise<void> {
    const result = await this.bridge.diff();
    if (result.success) {
      const text = result.stdout.trim() || "No changes detected.";
      new Notice(text, text.length > 100 ? 15000 : 5000);
    } else {
      new Notice(`Error: ${result.stderr}`, 5000);
    }
  }

  // ─── Status Bar ────────────────────────────────────────────

  private updateStatusBar(connected: boolean, proposalCount?: number): void {
    if (!this.statusBarEl) return;
    const dot = connected ? "is-connected" : "";
    let label = connected ? "ccoding" : "ccoding: not found";
    if (connected && proposalCount !== undefined && proposalCount > 0) {
      label = `ccoding: ${proposalCount} proposal${proposalCount !== 1 ? "s" : ""}`;
    }
    this.statusBarEl.innerHTML = "";
    this.statusBarEl.addClass("ccoding-status-bar");
    this.statusBarEl.createSpan({ cls: `ccoding-status-dot ${dot}` });
    this.statusBarEl.createSpan({ text: label });
  }

  /** Count proposals from current canvas data and update status bar. */
  private updateProposalCount(): void {
    if (!this.cliAvailable || !this.currentCanvas) {
      this.updateStatusBar(this.cliAvailable);
      return;
    }

    const data = this.currentCanvas.getData?.();
    if (!data) return;

    let count = 0;
    for (const node of data.nodes ?? []) {
      if (node.ccoding?.status === "proposed") count++;
    }
    for (const edge of data.edges ?? []) {
      if (edge.ccoding?.status === "proposed") count++;
    }

    this.updateStatusBar(true, count);
  }

  // ─── Canvas Lifecycle ──────────────────────────────────────

  /**
   * Run a CLI action and refresh the canvas afterward.
   */
  private async runAction(action: () => Promise<void>): Promise<void> {
    await action();
    this.refreshCanvas();
  }

  /**
   * Refresh the canvas view after external changes (CLI operations).
   */
  private refreshCanvas(): void {
    this.highlighter.detach();
    setTimeout(() => {
      this.tryAttachToCanvas();
      this.updateProposalCount();
    }, 150);
  }

  /**
   * Attempt to find an active canvas view and attach styling/watcher.
   */
  private tryAttachToCanvas(): void {
    const leaf = this.app.workspace.getMostRecentLeaf();
    if (!leaf) return;
    const view = leaf.view as any;
    if (!view?.canvas) return;

    const canvas = view.canvas;

    this.detachSelectionListener();

    const canvasData = canvas.getData?.() || { nodes: [], edges: [] };

    this.patcher.attach(canvas);

    this.highlighter.buildCache(canvasData);
    this.highlighter.attach(canvas);

    const filePath = view.file?.path;
    if (filePath) {
      this.watcher.start(this.app.vault, filePath);
    }

    this.currentCanvas = canvas;
    if (canvas.on) {
      this.selectionHandler = (selection: Set<any>) => {
        const selectedNode = selection?.size === 1
          ? Array.from(selection)[0]
          : null;
        this.highlighter.onSelectionChange(
          selectedNode?.id ?? null,
        );
      };
      canvas.on("selection-change", this.selectionHandler);
    }

    // Update proposal count in status bar
    this.updateProposalCount();
  }

  private detachSelectionListener(): void {
    if (this.currentCanvas && this.selectionHandler) {
      this.currentCanvas.off?.("selection-change", this.selectionHandler);
    }
    this.selectionHandler = null;
    this.currentCanvas = null;
  }

  private onCanvasFileChanged(): void {
    if (!this.settings.autoReloadOnChange) return;
    this.refreshCanvas();
  }

  private runLayout(all: boolean): void {
    const leaf = this.app.workspace.getMostRecentLeaf();
    if (!leaf) return;
    const view = leaf.view as any;
    if (!view?.canvas) return;

    const canvas = view.canvas;
    const data = canvas.getData?.();
    if (!data) return;

    const updated = layoutCanvas(
      data,
      all,
      this.settings.showRejectedNodes,
    );

    canvas.setData?.(updated);
    canvas.requestSave?.();

    this.refreshCanvas();
  }
}
