// src/main.ts
import { Plugin, Notice } from "obsidian";
import { type PluginSettings, DEFAULT_SETTINGS, parseCcodingMetadata, parseEdgeMetadata } from "./types";
import { CcodingSettingTab } from "./settings";
import { CcodingBridge } from "./bridge/cli";
import { CanvasWatcher } from "./watcher/canvas-watcher";
import { StyleInjector } from "./styling/injector";
import { ContextHighlighter } from "./highlight/context";
import { addNodeMenuItems, addEdgeMenuItems } from "./ghost/menu";
import {
  acceptAll,
  rejectAll,
  syncCanvas,
  checkStatus,
} from "./ghost/actions";
import { layoutCanvas } from "./layout/hierarchical";

export default class CooperativeCodingPlugin extends Plugin {
  settings: PluginSettings = DEFAULT_SETTINGS;
  bridge!: CcodingBridge;
  watcher!: CanvasWatcher;
  injector!: StyleInjector;
  highlighter!: ContextHighlighter;
  private cliAvailable = false;
  private selectionHandler: ((selection: Set<any>) => void) | null = null;
  private currentCanvas: any = null;

  async onload() {
    await this.loadSettings();
    this.bridge = new CcodingBridge(this.settings);
    this.injector = new StyleInjector(this.settings);
    this.highlighter = new ContextHighlighter();
    this.watcher = new CanvasWatcher(
      () => this.onCanvasFileChanged(),
      () => new Notice("Canvas file was deleted or renamed. Watcher stopped.", 5000),
    );

    // Settings tab
    this.addSettingTab(new CcodingSettingTab(this.app, this));

    // Set vault base path for project root auto-detection
    const basePath = (this.app.vault.adapter as any).getBasePath?.() || "";
    this.bridge.setVaultBasePath(basePath);

    // Check CLI availability (non-blocking)
    this.bridge.isAvailable().then((available) => {
      this.cliAvailable = available;
      if (!available) {
        new Notice(
          "ccoding CLI not found. Install it or set the path in CooperativeCoding plugin settings.",
          0,
        );
      }
    });

    // Register commands — use checkCallback to hide when CLI unavailable
    this.addCommand({
      id: "cooperative-coding:accept-all",
      name: "Accept all proposals",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) acceptAll(this.bridge);
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:reject-all",
      name: "Reject all proposals",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) rejectAll(this.bridge);
        return true;
      },
    });

    this.addCommand({
      id: "cooperative-coding:sync",
      name: "Sync",
      checkCallback: (checking: boolean) => {
        if (!this.cliAvailable) return false;
        if (!checking) syncCanvas(this.bridge);
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
      id: "cooperative-coding:layout",
      name: "Layout canvas",
      callback: () => this.runLayout(false),
    });

    this.addCommand({
      id: "cooperative-coding:layout-all",
      name: "Layout all nodes",
      callback: () => this.runLayout(true),
    });

    // Register canvas view event
    this.registerEvent(
      this.app.workspace.on("layout-change", () => {
        this.tryAttachToCanvas();
      }),
    );

    // Register context menu for canvas nodes
    this.registerEvent(
      this.app.workspace.on("canvas:node-menu" as any, (menu: any, node: any) => {
        if (!this.cliAvailable) return;
        const meta = parseCcodingMetadata(node?.unknownData?.ccoding);
        if (meta) {
          addNodeMenuItems(menu, node.id, meta, this.bridge);
        }
      }),
    );

    // Register context menu for canvas edges
    this.registerEvent(
      this.app.workspace.on("canvas:edge-menu" as any, (menu: any, edge: any) => {
        if (!this.cliAvailable) return;
        const meta = parseEdgeMetadata(edge?.unknownData?.ccoding);
        if (meta) {
          addEdgeMenuItems(menu, edge.id, meta, this.bridge);
        }
      }),
    );

    // Register context menu on canvas background for "Layout all nodes"
    this.registerEvent(
      this.app.workspace.on("canvas:menu" as any, (menu: any) => {
        menu.addItem((item: any) =>
          item
            .setTitle("Layout all nodes")
            .setIcon("layout-grid")
            .onClick(() => this.runLayout(true)),
        );
      }),
    );

    // Try to attach to an already-open canvas
    this.tryAttachToCanvas();
  }

  onunload() {
    this.detachSelectionListener();
    this.injector.detach();
    this.highlighter.detach();
    this.watcher.stop();
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
    this.bridge?.updateSettings(this.settings);
    this.injector?.updateSettings(this.settings);
  }

  /**
   * Attempt to find an active canvas view and attach styling/watcher.
   */
  private tryAttachToCanvas(): void {
    // Duck-type check for canvas view (use getMostRecentLeaf, not deprecated activeLeaf)
    const leaf = this.app.workspace.getMostRecentLeaf();
    if (!leaf) return;
    const view = leaf.view as any;
    if (!view?.canvas) return;

    const canvas = view.canvas;
    const canvasEl = view.contentEl?.querySelector(".canvas") as HTMLElement;
    if (!canvasEl) return;

    // Detach previous selection listener if we're re-attaching
    this.detachSelectionListener();

    // Read canvas data
    const canvasData = canvas.getData?.() || { nodes: [], edges: [] };

    // Attach styling
    this.injector.attach(canvasEl, canvasData);

    // Build context highlight cache
    this.highlighter.buildCache(canvasData);
    this.highlighter.attach(canvasEl);

    // Start file watcher
    const filePath = view.file?.path;
    if (filePath) {
      const fullPath = (this.app.vault.adapter as any).getBasePath?.() + "/" + filePath;
      if (fullPath) {
        this.watcher.start(fullPath);
      }
    }

    // Listen for selection changes (store handler for cleanup)
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
  }

  /**
   * Remove the selection change listener from the current canvas.
   */
  private detachSelectionListener(): void {
    if (this.currentCanvas && this.selectionHandler) {
      this.currentCanvas.off?.("selection-change", this.selectionHandler);
    }
    this.selectionHandler = null;
    this.currentCanvas = null;
  }

  private onCanvasFileChanged(): void {
    if (!this.settings.autoReloadOnChange) return;
    // Detach and re-attach to pick up new canvas data
    this.injector.detach();
    this.highlighter.detach();
    // Short delay to let Obsidian finish writing
    setTimeout(() => this.tryAttachToCanvas(), 100);
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

    // Write updated positions back to the canvas
    canvas.setData?.(updated);
    canvas.requestSave?.();

    // Re-attach styling
    this.injector.detach();
    this.highlighter.detach();
    setTimeout(() => this.tryAttachToCanvas(), 100);
  }
}
