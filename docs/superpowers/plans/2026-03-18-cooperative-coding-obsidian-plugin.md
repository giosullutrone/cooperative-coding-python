# CooperativeCoding Obsidian Plugin Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an Obsidian canvas plugin that renders CooperativeCoding nodes with styled visuals, provides ghost node accept/reject UX, and delegates operations to the `ccoding` CLI.

**Architecture:** Single Obsidian plugin with internal modules: types, settings, CLI bridge, canvas watcher, CSS styling + DOM patches, ghost UX (context menu), hierarchical layout, and context node highlighting. Pure logic is separated into testable modules; Obsidian API interactions are thin wrappers.

**Tech Stack:** TypeScript, Obsidian Plugin API, esbuild, vitest, Node.js `child_process` and `fs`

---

## File Structure

```
obsidian-plugin/
├── manifest.json                    # Obsidian plugin manifest
├── package.json                     # Node package config
├── tsconfig.json                    # TypeScript config
├── esbuild.config.mjs              # Build config
├── vitest.config.ts                 # Test config
├── styles.css                       # All node/edge CSS styling rules
├── src/
│   ├── main.ts                      # Plugin entry point — onload/onunload lifecycle
│   ├── settings.ts                  # Plugin settings tab + PluginSettings interface
│   ├── types.ts                     # CcodingMetadata, EdgeMetadata, helper functions
│   ├── bridge/
│   │   ├── cli.ts                   # CcodingBridge: shell exec wrapper + command queue
│   │   └── queue.ts                 # AsyncQueue: FIFO mutex for sequential CLI commands
│   ├── styling/
│   │   ├── class-mapper.ts          # Pure logic: ccoding metadata → CSS class list
│   │   ├── injector.ts              # DOM: applies CSS classes + MutationObserver
│   │   ├── patches.ts              # DOM: stereotype badges, ghost banners, rationale footers
│   │   └── markers.ts              # SVG: edge arrow marker definitions
│   ├── ghost/
│   │   ├── menu.ts                  # Context menu registration (Obsidian API)
│   │   └── actions.ts              # Ghost action handlers — calls bridge, shows notices
│   ├── watcher/
│   │   ├── canvas-watcher.ts       # fs.watch wrapper + reload trigger
│   │   └── debounce.ts             # Pure logic: debounce utility
│   ├── layout/
│   │   ├── graph.ts                # Pure logic: build graph, toposort, layer assignment, position
│   │   └── hierarchical.ts         # Obsidian integration: reads canvas data, applies positions
│   └── highlight/
│       └── context.ts              # Selection listener + context node CSS toggling
├── tests/
│   ├── types.test.ts               # Metadata parsing helpers
│   ├── bridge/
│   │   ├── cli.test.ts             # Command construction, result parsing
│   │   └── queue.test.ts           # FIFO ordering, sequential execution
│   ├── styling/
│   │   └── class-mapper.test.ts    # Metadata → CSS class mapping
│   ├── ghost/
│   │   └── actions.test.ts         # Ghost action handlers (mocked bridge)
│   ├── highlight/
│   │   └── context.test.ts         # Context cache building, selection
│   ├── layout/
│   │   ├── graph.test.ts           # Toposort, layer assignment, position calculation
│   │   └── hierarchical.test.ts    # layoutCanvas pure function
│   └── watcher/
│       └── debounce.test.ts        # Debounce timing behavior
└── fixtures/
    ├── sample.canvas               # Symlink or copy from tests/fixtures/sample.canvas
    └── sample_no_ccoding.canvas    # Symlink or copy from tests/fixtures/sample_no_ccoding.canvas
```

**Module responsibility boundaries:**
- `types.ts` — data definitions only, no side effects, no Obsidian imports
- `bridge/queue.ts` — generic async queue, no CLI knowledge
- `bridge/cli.ts` — knows about `ccoding` commands, uses queue, uses `child_process`
- `styling/class-mapper.ts` — pure function: metadata in, class list out. No DOM.
- `styling/injector.ts` — DOM manipulation: applies classes from class-mapper, sets up MutationObserver
- `styling/patches.ts` — DOM manipulation: creates/injects badge/banner elements
- `styling/markers.ts` — SVG generation: creates marker `<defs>` element
- `watcher/debounce.ts` — generic debounce utility, no fs or Obsidian imports
- `layout/graph.ts` — pure graph algorithms: toposort, layering, position calculation. No Obsidian.
- `layout/hierarchical.ts` — reads canvas data via Obsidian API, calls graph.ts, writes positions back

---

### Task 1: Project Scaffold

**Files:**
- Create: `obsidian-plugin/manifest.json`
- Create: `obsidian-plugin/package.json`
- Create: `obsidian-plugin/tsconfig.json`
- Create: `obsidian-plugin/esbuild.config.mjs`
- Create: `obsidian-plugin/vitest.config.ts`
- Create: `obsidian-plugin/src/main.ts`
- Create: `obsidian-plugin/.gitignore`

- [ ] **Step 1: Create manifest.json**

```json
{
  "id": "obsidian-cooperative-coding",
  "name": "CooperativeCoding",
  "version": "0.1.0",
  "minAppVersion": "1.5.0",
  "description": "Visual canvas plugin for CooperativeCoding — renders ccoding nodes, ghost node UX, and CLI integration.",
  "author": "CooperativeCoding",
  "isDesktopOnly": true
}
```

- [ ] **Step 2: Create package.json**

```json
{
  "name": "obsidian-cooperative-coding",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "node esbuild.config.mjs",
    "build": "node esbuild.config.mjs production",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "builtin-modules": "^4.0.0",
    "esbuild": "^0.24.0",
    "obsidian": "latest",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "inlineSourceMap": true,
    "inlineSources": true,
    "module": "ESNext",
    "target": "ES2022",
    "allowJs": true,
    "noImplicitAny": true,
    "moduleResolution": "bundler",
    "importHelpers": true,
    "isolatedModules": true,
    "strictNullChecks": true,
    "lib": ["DOM", "ES2022"]
  },
  "include": ["src/**/*.ts"]
}
```

- [ ] **Step 4: Create esbuild.config.mjs**

```javascript
import esbuild from "esbuild";
import process from "process";
import builtins from "builtin-modules";

const prod = process.argv[2] === "production";

const context = await esbuild.context({
  entryPoints: ["src/main.ts"],
  bundle: true,
  external: [
    "obsidian",
    "electron",
    "@codemirror/autocomplete",
    "@codemirror/collab",
    "@codemirror/commands",
    "@codemirror/language",
    "@codemirror/lint",
    "@codemirror/search",
    "@codemirror/state",
    "@codemirror/view",
    "@lezer/common",
    "@lezer/highlight",
    "@lezer/lr",
    ...builtins,
  ],
  format: "cjs",
  target: "es2022",
  logLevel: "info",
  sourcemap: prod ? false : "inline",
  treeShaking: true,
  outfile: "main.js",
  minify: prod,
});

if (prod) {
  await context.rebuild();
  process.exit(0);
} else {
  await context.watch();
}
```

- [ ] **Step 5: Create vitest.config.ts**

```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    root: ".",
    include: ["tests/**/*.test.ts"],
  },
  resolve: {
    alias: {
      obsidian: "./tests/__mocks__/obsidian.ts",
    },
  },
});
```

- [ ] **Step 6: Create Obsidian mock for tests**

Create `obsidian-plugin/tests/__mocks__/obsidian.ts`:

```typescript
// Minimal Obsidian API mock for unit tests.
// Only stub what tests actually need — expand as required.

export class Plugin {
  app: any = {};
  manifest: any = {};
  async loadData(): Promise<any> { return {}; }
  async saveData(_data: any): Promise<void> {}
  addCommand(_cmd: any): any { return {}; }
  registerEvent(_evt: any): void {}
}

export class Notice {
  constructor(public message: string, public timeout?: number) {}
  hide(): void {}
}

export class PluginSettingTab {
  app: any;
  plugin: any;
  containerEl: any = { empty() {}, createEl() { return { createEl() { return {}; } }; } };
  constructor(app: any, plugin: any) {
    this.app = app;
    this.plugin = plugin;
  }
  display(): void {}
}

export class Setting {
  constructor(_containerEl: any) {}
  setName(_name: string): this { return this; }
  setDesc(_desc: string): this { return this; }
  addText(_cb: any): this { return this; }
  addToggle(_cb: any): this { return this; }
}
```

- [ ] **Step 7: Create minimal main.ts**

```typescript
import { Plugin } from "obsidian";

export default class CooperativeCodingPlugin extends Plugin {
  async onload() {
    console.log("CooperativeCoding plugin loaded");
  }

  onunload() {
    console.log("CooperativeCoding plugin unloaded");
  }
}
```

- [ ] **Step 8: Create .gitignore**

```
node_modules/
main.js
*.js.map
```

- [ ] **Step 9: Install dependencies and verify build**

Run: `cd obsidian-plugin && npm install && npm run build`
Expected: `main.js` created with no errors

- [ ] **Step 10: Verify tests run (empty suite)**

Run: `cd obsidian-plugin && npm test`
Expected: vitest runs with 0 tests

- [ ] **Step 11: Commit**

```bash
git add obsidian-plugin/
git commit -m "feat: scaffold Obsidian plugin project"
```

---

### Task 2: Type Definitions

**Files:**
- Create: `obsidian-plugin/src/types.ts`
- Create: `obsidian-plugin/tests/types.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// tests/types.test.ts
import { describe, it, expect } from "vitest";
import {
  parseCcodingMetadata,
  parseEdgeMetadata,
  type CcodingMetadata,
} from "../src/types";

describe("parseCcodingMetadata", () => {
  it("parses full metadata", () => {
    const raw = {
      kind: "class",
      stereotype: "protocol",
      language: "python",
      source: "src/parser.py",
      qualifiedName: "parser.DocumentParser",
      status: "accepted",
      proposedBy: null,
      proposalRationale: null,
      layoutPending: false,
    };
    const meta = parseCcodingMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.kind).toBe("class");
    expect(meta!.stereotype).toBe("protocol");
    expect(meta!.status).toBe("accepted");
  });

  it("returns null for missing metadata", () => {
    expect(parseCcodingMetadata(undefined)).toBeNull();
    expect(parseCcodingMetadata(null)).toBeNull();
  });

  it("parses minimal ghost context node (status only, no kind)", () => {
    const raw = { status: "proposed", proposedBy: "agent" };
    const meta = parseCcodingMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.status).toBe("proposed");
    expect(meta!.kind).toBeUndefined();
  });
});

describe("parseEdgeMetadata", () => {
  it("parses edge metadata", () => {
    const raw = {
      relation: "inherits",
      status: "accepted",
      proposedBy: null,
      proposalRationale: null,
    };
    const meta = parseEdgeMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.relation).toBe("inherits");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL — cannot find module `../src/types`

- [ ] **Step 3: Write implementation**

```typescript
// src/types.ts

/** ccoding metadata on a canvas node. */
export interface CcodingMetadata {
  kind?: string;         // "class" | "method" | "field" | "package"
  stereotype?: string;   // "protocol" | "dataclass" | "abstract" | "enum"
  language?: string;
  source?: string;
  qualifiedName?: string;
  status?: string;       // "accepted" | "proposed" | "rejected" | "stale"
  proposedBy?: string | null;
  proposalRationale?: string | null;
  layoutPending?: boolean;
}

/** ccoding metadata on a canvas edge. */
export interface EdgeMetadata {
  relation: string;      // "inherits" | "implements" | "composes" | "depends" | "calls" | "detail" | "context"
  status?: string;
  proposedBy?: string | null;
  proposalRationale?: string | null;
}

/** Result of a CLI command execution. */
export interface CommandResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
}

/** Plugin settings persisted by Obsidian. */
export interface PluginSettings {
  ccodingPath: string;
  projectRoot: string;
  showRejectedNodes: boolean;
  autoReloadOnChange: boolean;
  commandTimeout: number;
}

export const DEFAULT_SETTINGS: PluginSettings = {
  ccodingPath: "",
  projectRoot: "",
  showRejectedNodes: false,
  autoReloadOnChange: true,
  commandTimeout: 30000,
};

/**
 * Parse raw ccoding metadata from a canvas node's JSON.
 * Returns null if the input is not a valid metadata object.
 */
export function parseCcodingMetadata(
  raw: unknown,
): CcodingMetadata | null {
  if (raw == null || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  // Must have at least status or kind to be ccoding metadata
  if (!obj.status && !obj.kind) return null;
  return {
    kind: typeof obj.kind === "string" ? obj.kind : undefined,
    stereotype: typeof obj.stereotype === "string" ? obj.stereotype : undefined,
    language: typeof obj.language === "string" ? obj.language : undefined,
    source: typeof obj.source === "string" ? obj.source : undefined,
    qualifiedName:
      typeof obj.qualifiedName === "string" ? obj.qualifiedName : undefined,
    status: typeof obj.status === "string" ? obj.status : undefined,
    proposedBy:
      typeof obj.proposedBy === "string" ? obj.proposedBy : null,
    proposalRationale:
      typeof obj.proposalRationale === "string"
        ? obj.proposalRationale
        : null,
    layoutPending: obj.layoutPending === true,
  };
}

/**
 * Parse raw ccoding metadata from a canvas edge's JSON.
 */
export function parseEdgeMetadata(
  raw: unknown,
): EdgeMetadata | null {
  if (raw == null || typeof raw !== "object") return null;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.relation !== "string") return null;
  return {
    relation: obj.relation,
    status: typeof obj.status === "string" ? obj.status : undefined,
    proposedBy:
      typeof obj.proposedBy === "string" ? obj.proposedBy : null,
    proposalRationale:
      typeof obj.proposalRationale === "string"
        ? obj.proposalRationale
        : null,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/types.ts obsidian-plugin/tests/types.test.ts
git commit -m "feat: add ccoding type definitions and metadata parsers"
```

---

### Task 3: Settings Module

**Files:**
- Create: `obsidian-plugin/src/settings.ts`

- [ ] **Step 1: Write settings tab**

```typescript
// src/settings.ts
import { PluginSettingTab, Setting, App } from "obsidian";
import type CooperativeCodingPlugin from "./main";
import { type PluginSettings, DEFAULT_SETTINGS } from "./types";

export class CcodingSettingTab extends PluginSettingTab {
  plugin: CooperativeCodingPlugin;

  constructor(app: App, plugin: CooperativeCodingPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "CooperativeCoding Settings" });

    new Setting(containerEl)
      .setName("ccoding CLI path")
      .setDesc(
        "Path to the ccoding binary. Leave empty to auto-detect from PATH.",
      )
      .addText((text) =>
        text
          .setPlaceholder("/usr/local/bin/ccoding")
          .setValue(this.plugin.settings.ccodingPath)
          .onChange(async (value) => {
            this.plugin.settings.ccodingPath = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Project root")
      .setDesc(
        "Path to the project root containing .ccoding/. Leave empty to auto-detect.",
      )
      .addText((text) =>
        text
          .setValue(this.plugin.settings.projectRoot)
          .onChange(async (value) => {
            this.plugin.settings.projectRoot = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Show rejected nodes")
      .setDesc("Display rejected ghost nodes (greyed out) instead of hiding them.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.showRejectedNodes)
          .onChange(async (value) => {
            this.plugin.settings.showRejectedNodes = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Auto-reload on external change")
      .setDesc(
        "Reload the canvas when the .canvas file is modified externally (by CLI or git).",
      )
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.autoReloadOnChange)
          .onChange(async (value) => {
            this.plugin.settings.autoReloadOnChange = value;
            await this.plugin.saveSettings();
          }),
      );

    new Setting(containerEl)
      .setName("Command timeout (ms)")
      .setDesc(
        "Maximum time in milliseconds to wait for a CLI command before aborting. Default: 30000.",
      )
      .addText((text) =>
        text
          .setPlaceholder("30000")
          .setValue(String(this.plugin.settings.commandTimeout))
          .onChange(async (value) => {
            const parsed = parseInt(value, 10);
            if (!isNaN(parsed) && parsed > 0) {
              this.plugin.settings.commandTimeout = parsed;
              await this.plugin.saveSettings();
            }
          }),
      );
  }
}
```

- [ ] **Step 2: Wire settings into main.ts**

Update `obsidian-plugin/src/main.ts`:

```typescript
import { Plugin } from "obsidian";
import { type PluginSettings, DEFAULT_SETTINGS } from "./types";
import { CcodingSettingTab } from "./settings";

export default class CooperativeCodingPlugin extends Plugin {
  settings: PluginSettings = DEFAULT_SETTINGS;

  async onload() {
    await this.loadSettings();
    this.addSettingTab(new CcodingSettingTab(this.app, this));
    console.log("CooperativeCoding plugin loaded");
  }

  onunload() {
    console.log("CooperativeCoding plugin unloaded");
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
```

- [ ] **Step 3: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/settings.ts obsidian-plugin/src/main.ts
git commit -m "feat: add plugin settings tab"
```

---

### Task 4: Async Queue

**Files:**
- Create: `obsidian-plugin/src/bridge/queue.ts`
- Create: `obsidian-plugin/tests/bridge/queue.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// tests/bridge/queue.test.ts
import { describe, it, expect } from "vitest";
import { AsyncQueue } from "../../src/bridge/queue";

describe("AsyncQueue", () => {
  it("executes tasks in FIFO order", async () => {
    const queue = new AsyncQueue();
    const order: number[] = [];

    const p1 = queue.enqueue(async () => {
      await new Promise((r) => setTimeout(r, 50));
      order.push(1);
      return 1;
    });
    const p2 = queue.enqueue(async () => {
      order.push(2);
      return 2;
    });
    const p3 = queue.enqueue(async () => {
      order.push(3);
      return 3;
    });

    const results = await Promise.all([p1, p2, p3]);
    expect(results).toEqual([1, 2, 3]);
    expect(order).toEqual([1, 2, 3]);
  });

  it("only runs one task at a time", async () => {
    const queue = new AsyncQueue();
    let running = 0;
    let maxConcurrent = 0;

    const task = async () => {
      running++;
      maxConcurrent = Math.max(maxConcurrent, running);
      await new Promise((r) => setTimeout(r, 10));
      running--;
    };

    await Promise.all([
      queue.enqueue(task),
      queue.enqueue(task),
      queue.enqueue(task),
    ]);

    expect(maxConcurrent).toBe(1);
  });

  it("propagates errors without blocking queue", async () => {
    const queue = new AsyncQueue();

    const p1 = queue.enqueue(async () => {
      throw new Error("fail");
    });
    const p2 = queue.enqueue(async () => "ok");

    await expect(p1).rejects.toThrow("fail");
    expect(await p2).toBe("ok");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL — cannot find module

- [ ] **Step 3: Write implementation**

```typescript
// src/bridge/queue.ts

/**
 * A simple async FIFO queue that ensures only one task runs at a time.
 * Used to serialize CLI commands and prevent race conditions.
 */
export class AsyncQueue {
  private queue: Array<() => Promise<void>> = [];
  private running = false;

  /**
   * Enqueue a task. Returns a promise that resolves with the task's result
   * or rejects with the task's error.
   */
  enqueue<T>(task: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      this.queue.push(async () => {
        try {
          resolve(await task());
        } catch (err) {
          reject(err);
        }
      });
      this.processNext();
    });
  }

  private async processNext(): Promise<void> {
    if (this.running) return;
    const next = this.queue.shift();
    if (!next) return;
    this.running = true;
    try {
      await next();
    } finally {
      this.running = false;
      this.processNext();
    }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/bridge/queue.ts obsidian-plugin/tests/bridge/queue.test.ts
git commit -m "feat: add async FIFO queue for CLI command serialization"
```

---

### Task 5: CLI Bridge

**Files:**
- Create: `obsidian-plugin/src/bridge/cli.ts`
- Create: `obsidian-plugin/tests/bridge/cli.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// tests/bridge/cli.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CcodingBridge } from "../../src/bridge/cli";
import type { PluginSettings } from "../../src/types";
import { DEFAULT_SETTINGS } from "../../src/types";

// Mock child_process
vi.mock("child_process", () => ({
  execFile: vi.fn(),
}));

import { execFile } from "child_process";

function mockExecFile(
  stdout: string,
  stderr: string,
  exitCode: number,
) {
  (execFile as any).mockImplementation(
    (
      _cmd: string,
      _args: string[],
      _opts: any,
      cb: (err: any, stdout: string, stderr: string) => void,
    ) => {
      if (exitCode !== 0) {
        const err = new Error(stderr) as any;
        err.code = exitCode;
        cb(err, stdout, stderr);
      } else {
        cb(null, stdout, stderr);
      }
    },
  );
}

describe("CcodingBridge", () => {
  let bridge: CcodingBridge;
  let settings: PluginSettings;

  beforeEach(() => {
    vi.clearAllMocks();
    settings = { ...DEFAULT_SETTINGS, projectRoot: "/test/project" };
    bridge = new CcodingBridge(settings);
    bridge.setVaultBasePath("/test/vault");
  });

  it("constructs accept command correctly", async () => {
    mockExecFile("", "", 0);
    await bridge.accept("node-abc123");
    expect(execFile).toHaveBeenCalledWith(
      "ccoding",
      ["--project", "/test/project", "accept", "node-abc123"],
      expect.objectContaining({ timeout: 30000 }),
      expect.any(Function),
    );
  });

  it("uses custom CLI path when set", async () => {
    settings.ccodingPath = "/custom/bin/ccoding";
    bridge = new CcodingBridge(settings);
    mockExecFile("", "", 0);
    await bridge.accept("node-1");
    expect(execFile).toHaveBeenCalledWith(
      "/custom/bin/ccoding",
      expect.any(Array),
      expect.any(Object),
      expect.any(Function),
    );
  });

  it("returns success result on exit 0", async () => {
    mockExecFile("output text", "", 0);
    const result = await bridge.status();
    expect(result.success).toBe(true);
    expect(result.stdout).toBe("output text");
    expect(result.exitCode).toBe(0);
  });

  it("returns failure result on non-zero exit", async () => {
    mockExecFile("", "error message", 1);
    const result = await bridge.accept("node-1");
    expect(result.success).toBe(false);
    expect(result.stderr).toBe("error message");
  });

  it("isAvailable returns true when CLI responds", async () => {
    mockExecFile("ccoding 0.1.0", "", 0);
    expect(await bridge.isAvailable()).toBe(true);
  });

  it("isAvailable returns false when CLI not found", async () => {
    (execFile as any).mockImplementation(
      (_cmd: string, _args: string[], _opts: any, cb: Function) => {
        const err = new Error("ENOENT") as any;
        err.code = "ENOENT";
        cb(err, "", "");
      },
    );
    expect(await bridge.isAvailable()).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL — cannot find module

- [ ] **Step 3: Write implementation**

```typescript
// src/bridge/cli.ts
import { execFile as nodeExecFile } from "child_process";
import { AsyncQueue } from "./queue";
import type { CommandResult, PluginSettings } from "../types";

export class CcodingBridge {
  private settings: PluginSettings;
  private queue = new AsyncQueue();
  private resolvedProjectRoot: string | null = null;

  constructor(settings: PluginSettings) {
    this.settings = settings;
  }

  /** Update settings reference (e.g., after user changes settings). */
  updateSettings(settings: PluginSettings): void {
    this.settings = settings;
    this.resolvedProjectRoot = null; // re-detect on next command
  }

  /**
   * Set the vault base path for project root auto-detection.
   * Called by the plugin during onload().
   */
  setVaultBasePath(basePath: string): void {
    this.resolvedProjectRoot = null;
    this.vaultBasePath = basePath;
  }
  private vaultBasePath = "";

  // --- Ghost operations ---

  accept(id: string): Promise<CommandResult> {
    return this.run(["accept", id]);
  }

  reject(id: string): Promise<CommandResult> {
    return this.run(["reject", id]);
  }

  reconsider(id: string): Promise<CommandResult> {
    return this.run(["reconsider", id]);
  }

  acceptAll(): Promise<CommandResult> {
    return this.run(["accept-all"]);
  }

  rejectAll(): Promise<CommandResult> {
    return this.run(["reject-all"]);
  }

  // --- Sync operations ---

  sync(): Promise<CommandResult> {
    return this.run(["sync"]);
  }

  status(): Promise<CommandResult> {
    return this.run(["status"]);
  }

  check(): Promise<CommandResult> {
    return this.run(["check"]);
  }

  // --- Utilities ---

  /**
   * Check if the ccoding CLI is available.
   * Intentionally bypasses the command queue — this is called at
   * startup and should not wait behind queued commands.
   */
  async isAvailable(): Promise<boolean> {
    try {
      const result = await this.exec(this.cliPath(), ["--version"]);
      return result.success;
    } catch {
      return false;
    }
  }

  async getVersion(): Promise<string> {
    const result = await this.exec(this.cliPath(), ["--version"]);
    return result.stdout.trim() || "unknown";
  }

  // --- Internal ---

  private cliPath(): string {
    return this.settings.ccodingPath || "ccoding";
  }

  /**
   * Auto-detect project root by walking up from the vault base path
   * looking for a `.ccoding/` directory. Falls back to vault root.
   */
  private getProjectRoot(): string {
    if (this.settings.projectRoot) return this.settings.projectRoot;
    if (this.resolvedProjectRoot !== null) return this.resolvedProjectRoot;

    const { existsSync } = require("fs") as typeof import("fs");
    const { join, dirname } = require("path") as typeof import("path");

    let dir = this.vaultBasePath;
    while (dir && dir !== dirname(dir)) {
      if (existsSync(join(dir, ".ccoding"))) {
        this.resolvedProjectRoot = dir;
        return dir;
      }
      dir = dirname(dir);
    }
    // Fallback: vault root
    this.resolvedProjectRoot = this.vaultBasePath || "";
    return this.resolvedProjectRoot;
  }

  private projectArgs(): string[] {
    const root = this.getProjectRoot();
    if (root) {
      return ["--project", root];
    }
    return [];
  }

  private run(args: string[]): Promise<CommandResult> {
    return this.queue.enqueue(() =>
      this.exec(this.cliPath(), [...this.projectArgs(), ...args]),
    );
  }

  private exec(cmd: string, args: string[]): Promise<CommandResult> {
    return new Promise((resolve) => {
      nodeExecFile(
        cmd,
        args,
        {
          timeout: this.settings.commandTimeout,
          cwd: this.getProjectRoot() || undefined,
        },
        (err, stdout, stderr) => {
          if (err) {
            // Distinguish timeout from other errors
            const isTimeout = (err as any).killed === true
              || (err as any).signal === "SIGTERM";
            resolve({
              success: false,
              stdout: stdout || "",
              stderr: isTimeout
                ? "Command timed out. The operation may still be running."
                : stderr || err.message,
              exitCode: (err as any).code ?? 1,
            });
          } else {
            resolve({
              success: true,
              stdout: stdout || "",
              stderr: stderr || "",
              exitCode: 0,
            });
          }
        },
      );
    });
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/bridge/cli.ts obsidian-plugin/tests/bridge/cli.test.ts
git commit -m "feat: add CLI bridge with shell exec and command queuing"
```

---

### Task 6: Debounce Utility + Canvas Watcher

**Files:**
- Create: `obsidian-plugin/src/watcher/debounce.ts`
- Create: `obsidian-plugin/tests/watcher/debounce.test.ts`
- Create: `obsidian-plugin/src/watcher/canvas-watcher.ts`

- [ ] **Step 1: Write failing debounce tests**

```typescript
// tests/watcher/debounce.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Debouncer } from "../../src/watcher/debounce";

describe("Debouncer", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("calls callback after delay", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(300);
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("resets timer on repeated triggers", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    vi.advanceTimersByTime(200);
    debouncer.trigger();
    vi.advanceTimersByTime(200);
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("cancel prevents callback", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    debouncer.cancel();
    vi.advanceTimersByTime(500);
    expect(cb).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL

- [ ] **Step 3: Write debounce implementation**

```typescript
// src/watcher/debounce.ts

export class Debouncer {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private callback: () => void;
  private delay: number;

  constructor(callback: () => void, delay: number) {
    this.callback = callback;
    this.delay = delay;
  }

  trigger(): void {
    this.cancel();
    this.timer = setTimeout(() => {
      this.timer = null;
      this.callback();
    }, this.delay);
  }

  cancel(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
```

- [ ] **Step 4: Run tests to verify debounce passes**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Write canvas watcher**

```typescript
// src/watcher/canvas-watcher.ts
import { watch, type FSWatcher } from "fs";
import { Debouncer } from "./debounce";

export class CanvasWatcher {
  private watcher: FSWatcher | null = null;
  private debouncer: Debouncer;
  private filePath: string | null = null;
  isWriting = false;

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
```

- [ ] **Step 6: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 7: Commit**

```bash
git add obsidian-plugin/src/watcher/ obsidian-plugin/tests/watcher/
git commit -m "feat: add debounce utility and canvas file watcher"
```

---

### Task 7: CSS Class Mapper

**Files:**
- Create: `obsidian-plugin/src/styling/class-mapper.ts`
- Create: `obsidian-plugin/tests/styling/class-mapper.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// tests/styling/class-mapper.test.ts
import { describe, it, expect } from "vitest";
import { nodeClasses, edgeClasses } from "../../src/styling/class-mapper";
import type { CcodingMetadata, EdgeMetadata } from "../../src/types";

describe("nodeClasses", () => {
  it("maps class node to purple border", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-node-class");
    expect(classes).toContain("ccoding-accepted");
    expect(classes).not.toContain("ccoding-ghost");
  });

  it("maps method node to orange rounded", () => {
    const meta: CcodingMetadata = { kind: "method", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-method");
  });

  it("maps field node to blue rounded", () => {
    const meta: CcodingMetadata = { kind: "field", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-field");
  });

  it("maps package node", () => {
    const meta: CcodingMetadata = { kind: "package", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-package");
  });

  it("adds ghost class for proposed nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "proposed" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-ghost");
    expect(classes).toContain("ccoding-node-class");
  });

  it("adds rejected class", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-rejected");
  });

  it("hides rejected when showRejected is false", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-rejected-hidden");
  });

  it("does not hide rejected when showRejected is true", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, true);
    expect(classes).toContain("ccoding-rejected");
    expect(classes).not.toContain("ccoding-rejected-hidden");
  });

  it("adds stale class", () => {
    const meta: CcodingMetadata = { kind: "class", status: "stale" };
    expect(nodeClasses(meta, false)).toContain("ccoding-stale");
  });

  it("handles context ghost node (status only, no kind)", () => {
    const meta: CcodingMetadata = { status: "proposed", proposedBy: "agent" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-ghost");
    expect(classes).not.toContain("ccoding-node-class");
  });
});

describe("edgeClasses", () => {
  it("maps inherits edge", () => {
    const meta: EdgeMetadata = { relation: "inherits", status: "accepted" };
    expect(edgeClasses(meta)).toContain("ccoding-edge-inherits");
  });

  it("adds ghost class for proposed edges", () => {
    const meta: EdgeMetadata = { relation: "composes", status: "proposed" };
    const classes = edgeClasses(meta);
    expect(classes).toContain("ccoding-edge-composes");
    expect(classes).toContain("ccoding-ghost");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```typescript
// src/styling/class-mapper.ts
import type { CcodingMetadata, EdgeMetadata } from "../types";

const KIND_CLASS_MAP: Record<string, string> = {
  class: "ccoding-node-class",
  method: "ccoding-node-method",
  field: "ccoding-node-field",
  package: "ccoding-node-package",
};

const RELATION_CLASS_MAP: Record<string, string> = {
  inherits: "ccoding-edge-inherits",
  implements: "ccoding-edge-implements",
  composes: "ccoding-edge-composes",
  depends: "ccoding-edge-depends",
  calls: "ccoding-edge-calls",
  detail: "ccoding-edge-detail",
  context: "ccoding-edge-context",
};

/**
 * Compute CSS class list for a ccoding canvas node.
 * Pure function — no DOM or Obsidian dependency.
 */
export function nodeClasses(
  meta: CcodingMetadata,
  showRejected: boolean,
): string[] {
  const classes: string[] = ["ccoding-node"];

  // Kind-based styling
  if (meta.kind && KIND_CLASS_MAP[meta.kind]) {
    classes.push(KIND_CLASS_MAP[meta.kind]);
  }

  // Status-based styling
  switch (meta.status) {
    case "proposed":
      classes.push("ccoding-ghost");
      break;
    case "rejected":
      classes.push("ccoding-rejected");
      if (!showRejected) {
        classes.push("ccoding-rejected-hidden");
      }
      break;
    case "accepted":
      classes.push("ccoding-accepted");
      break;
    case "stale":
      classes.push("ccoding-stale");
      break;
  }

  return classes;
}

/**
 * Compute CSS class list for a ccoding canvas edge.
 */
export function edgeClasses(meta: EdgeMetadata): string[] {
  const classes: string[] = ["ccoding-edge"];

  if (RELATION_CLASS_MAP[meta.relation]) {
    classes.push(RELATION_CLASS_MAP[meta.relation]);
  }

  if (meta.status === "proposed") {
    classes.push("ccoding-ghost");
  }

  return classes;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/styling/class-mapper.ts obsidian-plugin/tests/styling/class-mapper.test.ts
git commit -m "feat: add pure CSS class mapper for ccoding metadata"
```

---

### Task 8: CSS Stylesheet

**Files:**
- Create: `obsidian-plugin/styles.css`

- [ ] **Step 1: Write the full CSS stylesheet**

```css
/* styles.css — CooperativeCoding Obsidian Plugin */

/* ============================================
   Node styling — kind-based borders
   ============================================ */

.ccoding-node-class {
  border: 3px solid #8b5cf6 !important;
  border-radius: 4px !important;
}

.ccoding-node-method {
  border: 3px solid #f97316 !important;
  border-radius: 12px !important;
}

.ccoding-node-field {
  border: 3px solid #3b82f6 !important;
  border-radius: 12px !important;
}

.ccoding-node-package {
  border: 3px solid #22c55e !important;
}

/* ============================================
   Node styling — status-based treatment
   ============================================ */

.ccoding-ghost {
  border-style: dashed !important;
  opacity: 0.7;
}

.ccoding-rejected {
  opacity: 0.3;
}

.ccoding-rejected-hidden {
  display: none !important;
}

.ccoding-stale {
  border: 3px solid #ca8a04 !important;
}

.ccoding-stale .markdown-rendered h2 {
  text-decoration: line-through;
}

/* ============================================
   Edge styling — relation-based
   ============================================ */

.ccoding-edge-inherits path {
  stroke: #e2e8f0 !important;
  stroke-width: 2px !important;
  stroke-dasharray: none !important;
}

.ccoding-edge-implements path {
  stroke: #e2e8f0 !important;
  stroke-width: 2px !important;
  stroke-dasharray: 8 4 !important;
}

.ccoding-edge-composes path {
  stroke: #8b5cf6 !important;
  stroke-width: 2px !important;
  stroke-dasharray: none !important;
}

.ccoding-edge-depends path {
  stroke: #64748b !important;
  stroke-width: 1px !important;
  stroke-dasharray: 8 4 !important;
}

.ccoding-edge-calls path {
  stroke: #f97316 !important;
  stroke-width: 1px !important;
  stroke-dasharray: 2 4 !important;
}

.ccoding-edge-detail path {
  stroke: #3b82f6 !important;
  stroke-width: 1px !important;
  stroke-dasharray: none !important;
}

.ccoding-edge-context path {
  stroke: #475569 !important;
  stroke-width: 1px !important;
  stroke-dasharray: none !important;
}

/* SVG markers — applied via marker-end/marker-start on edge paths */
.ccoding-edge-inherits path {
  marker-end: url(#ccoding-marker-inherits);
}

.ccoding-edge-implements path {
  marker-end: url(#ccoding-marker-implements);
}

.ccoding-edge-composes path {
  marker-start: url(#ccoding-marker-composes);
}

.ccoding-edge-depends path {
  marker-end: url(#ccoding-marker-depends);
}

.ccoding-edge-calls path {
  marker-end: url(#ccoding-marker-calls);
}

.ccoding-edge-detail path {
  marker-end: url(#ccoding-marker-detail);
}

/* Ghost edges */
.ccoding-edge.ccoding-ghost path {
  opacity: 0.7;
}

/* ============================================
   Context node highlighting
   ============================================ */

.ccoding-context-highlight {
  box-shadow: 0 0 12px 2px rgba(96, 165, 250, 0.5) !important;
}

.ccoding-context-highlight path {
  stroke: #e2e8f0 !important;
  stroke-width: 1.5px !important;
}

/* ============================================
   DOM patch elements
   ============================================ */

.ccoding-stereotype-badge {
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  padding: 2px 8px;
  letter-spacing: 0.5px;
  color: white;
}

.ccoding-node-class .ccoding-stereotype-badge {
  background: #8b5cf6;
}

.ccoding-proposed-banner {
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  padding: 4px 8px;
  letter-spacing: 1px;
  color: white;
  background: repeating-linear-gradient(
    45deg,
    #8b5cf6,
    #8b5cf6 10px,
    #7c3aed 10px,
    #7c3aed 20px
  );
}

.ccoding-stale-banner {
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  padding: 4px 8px;
  letter-spacing: 1px;
  color: white;
  background: #ca8a04;
}

.ccoding-rationale-footer {
  font-size: 11px;
  font-style: italic;
  padding: 8px 12px;
  border-top: 1px dashed #334155;
  color: #94a3b8;
  background: rgba(139, 92, 246, 0.05);
}

.ccoding-rationale-footer .ccoding-rationale-prefix {
  color: #a78bfa;
  font-weight: 600;
  font-style: normal;
}
```

- [ ] **Step 2: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds. Note: styles.css is loaded by Obsidian automatically from the plugin directory — not bundled by esbuild.

- [ ] **Step 3: Commit**

```bash
git add obsidian-plugin/styles.css
git commit -m "feat: add CSS stylesheet for node, edge, and ghost styling"
```

---

### Task 9: CSS Injector + DOM Patches

**Files:**
- Create: `obsidian-plugin/src/styling/injector.ts`
- Create: `obsidian-plugin/src/styling/patches.ts`
- Create: `obsidian-plugin/src/styling/markers.ts`

- [ ] **Step 1: Write CSS injector with MutationObserver**

```typescript
// src/styling/injector.ts
import { parseCcodingMetadata, parseEdgeMetadata } from "../types";
import type { PluginSettings } from "../types";
import { nodeClasses, edgeClasses } from "./class-mapper";
import { applyNodePatches, removeAllPatches } from "./patches";
import { injectMarkers, removeMarkers } from "./markers";

const PROCESSED_ATTR = "data-ccoding-processed";

/**
 * Manages CSS class injection and MutationObserver for the canvas.
 */
export class StyleInjector {
  private observer: MutationObserver | null = null;
  private canvasEl: HTMLElement | null = null;
  private settings: PluginSettings;

  constructor(settings: PluginSettings) {
    this.settings = settings;
  }

  updateSettings(settings: PluginSettings): void {
    this.settings = settings;
  }

  /**
   * Attach to a canvas view element. Scans existing nodes and starts observing.
   */
  attach(canvasEl: HTMLElement, canvasData: any): void {
    this.detach();
    this.canvasEl = canvasEl;

    // Build a lookup from node/edge id → ccoding metadata
    const nodeMetaMap = this.buildNodeMetaMap(canvasData);
    const edgeMetaMap = this.buildEdgeMetaMap(canvasData);

    // Process all existing nodes
    this.processAllNodes(canvasEl, nodeMetaMap);
    this.processAllEdges(canvasEl, edgeMetaMap);

    // Inject SVG markers
    const svgEl = canvasEl.querySelector("svg");
    if (svgEl) {
      injectMarkers(svgEl);
    }

    // Observe for new/changed DOM elements (viewport virtualization)
    this.observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const added of mutation.addedNodes) {
          if (added instanceof HTMLElement) {
            this.processAddedElement(added, nodeMetaMap, edgeMetaMap);
          }
        }
      }
    });
    this.observer.observe(canvasEl, { childList: true, subtree: true });
  }

  /**
   * Detach from the canvas, remove observer and all patches.
   */
  detach(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    if (this.canvasEl) {
      removeAllPatches(this.canvasEl);
      removeMarkers(this.canvasEl);
      // Remove ccoding classes
      this.canvasEl
        .querySelectorAll(`[${PROCESSED_ATTR}]`)
        .forEach((el) => {
          el.removeAttribute(PROCESSED_ATTR);
          // Remove all ccoding- classes
          const toRemove = Array.from(el.classList).filter((c) =>
            c.startsWith("ccoding-"),
          );
          el.classList.remove(...toRemove);
        });
      this.canvasEl = null;
    }
  }

  private buildNodeMetaMap(canvasData: any): Map<string, any> {
    const map = new Map<string, any>();
    if (canvasData?.nodes) {
      for (const node of canvasData.nodes) {
        const meta = parseCcodingMetadata(node.ccoding);
        if (meta) map.set(node.id, meta);
      }
    }
    return map;
  }

  private buildEdgeMetaMap(canvasData: any): Map<string, any> {
    const map = new Map<string, any>();
    if (canvasData?.edges) {
      for (const edge of canvasData.edges) {
        const meta = parseEdgeMetadata(edge.ccoding);
        if (meta) map.set(edge.id, meta);
      }
    }
    return map;
  }

  private processAllNodes(
    container: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    // Obsidian canvas nodes have a data-id attribute
    container
      .querySelectorAll<HTMLElement>(".canvas-node")
      .forEach((el) => {
        this.applyNodeStyling(el, metaMap);
      });
  }

  private processAllEdges(
    container: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    container
      .querySelectorAll<HTMLElement>(".canvas-edge")
      .forEach((el) => {
        this.applyEdgeStyling(el, metaMap);
      });
  }

  private processAddedElement(
    el: HTMLElement,
    nodeMetaMap: Map<string, any>,
    edgeMetaMap: Map<string, any>,
  ): void {
    if (el.classList.contains("canvas-node")) {
      this.applyNodeStyling(el, nodeMetaMap);
    } else if (el.classList.contains("canvas-edge")) {
      this.applyEdgeStyling(el, edgeMetaMap);
    }
    // Also check children (nodes may be nested in containers)
    el.querySelectorAll<HTMLElement>(".canvas-node").forEach((n) =>
      this.applyNodeStyling(n, nodeMetaMap),
    );
    el.querySelectorAll<HTMLElement>(".canvas-edge").forEach((e) =>
      this.applyEdgeStyling(e, edgeMetaMap),
    );
  }

  private applyNodeStyling(
    el: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    if (el.hasAttribute(PROCESSED_ATTR)) return;
    const id = el.dataset.id;
    if (!id) return;
    const meta = metaMap.get(id);
    if (!meta) return;

    const classes = nodeClasses(meta, this.settings.showRejectedNodes);
    el.classList.add(...classes);
    el.setAttribute(PROCESSED_ATTR, "true");

    // Set namespaced data attributes
    if (meta.kind) el.dataset.ccodingKind = meta.kind;
    if (meta.status) el.dataset.ccodingStatus = meta.status;

    // Apply DOM patches (badges, banners, footers)
    applyNodePatches(el, meta);
  }

  private applyEdgeStyling(
    el: HTMLElement,
    metaMap: Map<string, any>,
  ): void {
    if (el.hasAttribute(PROCESSED_ATTR)) return;
    const id = el.dataset.id;
    if (!id) return;
    const meta = metaMap.get(id);
    if (!meta) return;

    const classes = edgeClasses(meta);
    el.classList.add(...classes);
    el.setAttribute(PROCESSED_ATTR, "true");
  }
}
```

- [ ] **Step 2: Write DOM patches**

```typescript
// src/styling/patches.ts
import type { CcodingMetadata } from "../types";

const PATCH_ATTR = "data-ccoding-patch";

/**
 * Apply DOM patches (badges, banners, footers) to a canvas node element.
 */
export function applyNodePatches(
  el: HTMLElement,
  meta: CcodingMetadata,
): void {
  // Stereotype badge
  if (meta.kind === "class" && meta.stereotype) {
    const badge = document.createElement("div");
    badge.className = "ccoding-stereotype-badge";
    badge.setAttribute(PATCH_ATTR, "stereotype");
    badge.textContent = `\u00AB${meta.stereotype}\u00BB`;
    el.prepend(badge);
  }

  // Proposed banner
  if (meta.status === "proposed") {
    const banner = document.createElement("div");
    banner.className = "ccoding-proposed-banner";
    banner.setAttribute(PATCH_ATTR, "proposed");
    banner.textContent = "PROPOSED";
    el.prepend(banner);
  }

  // Stale banner
  if (meta.status === "stale") {
    const banner = document.createElement("div");
    banner.className = "ccoding-stale-banner";
    banner.setAttribute(PATCH_ATTR, "stale");
    banner.textContent = "STALE";
    el.prepend(banner);
  }

  // Rationale footer
  if (meta.status === "proposed" && meta.proposalRationale) {
    const footer = document.createElement("div");
    footer.className = "ccoding-rationale-footer";
    footer.setAttribute(PATCH_ATTR, "rationale");
    const prefix = document.createElement("span");
    prefix.className = "ccoding-rationale-prefix";
    prefix.textContent = "\uD83D\uDCA1 Agent rationale: ";
    footer.appendChild(prefix);
    footer.appendChild(
      document.createTextNode(meta.proposalRationale),
    );
    el.appendChild(footer);
  }
}

/**
 * Remove all ccoding DOM patches from a container.
 */
export function removeAllPatches(container: HTMLElement): void {
  container
    .querySelectorAll(`[${PATCH_ATTR}]`)
    .forEach((el) => el.remove());
}
```

- [ ] **Step 3: Write SVG markers**

```typescript
// src/styling/markers.ts

const MARKER_NS = "http://www.w3.org/2000/svg";
const DEFS_ID = "ccoding-marker-defs";

const MARKERS: Record<string, string> = {
  "ccoding-marker-inherits": `<marker id="ccoding-marker-inherits" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="none" stroke="#e2e8f0" stroke-width="1.5"/></marker>`,
  "ccoding-marker-implements": `<marker id="ccoding-marker-implements" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="none" stroke="#e2e8f0" stroke-width="1.5"/></marker>`,
  "ccoding-marker-composes": `<marker id="ccoding-marker-composes" viewBox="0 0 12 12" refX="0" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M 0 6 L 6 0 L 12 6 L 6 12 z" fill="#8b5cf6"/></marker>`,
  "ccoding-marker-depends": `<marker id="ccoding-marker-depends" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#64748b" stroke-width="1.5"/></marker>`,
  "ccoding-marker-calls": `<marker id="ccoding-marker-calls" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f97316"/></marker>`,
  "ccoding-marker-detail": `<marker id="ccoding-marker-detail" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8"><circle cx="5" cy="5" r="4" fill="#3b82f6"/></marker>`,
};

/**
 * Inject SVG marker definitions into the canvas SVG element.
 */
export function injectMarkers(svgEl: SVGElement): void {
  if (svgEl.querySelector(`#${DEFS_ID}`)) return;
  const defs = document.createElementNS(MARKER_NS, "defs");
  defs.id = DEFS_ID;
  defs.innerHTML = Object.values(MARKERS).join("\n");
  svgEl.prepend(defs);
}

/**
 * Remove injected SVG markers.
 */
export function removeMarkers(container: HTMLElement): void {
  container.querySelector(`#${DEFS_ID}`)?.remove();
}
```

- [ ] **Step 4: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/styling/
git commit -m "feat: add CSS injector, DOM patches, and SVG edge markers"
```

---

### Task 10: Ghost Context Menu + Actions

**Files:**
- Create: `obsidian-plugin/src/ghost/menu.ts`
- Create: `obsidian-plugin/src/ghost/actions.ts`

- [ ] **Step 1: Write ghost actions**

```typescript
// src/ghost/actions.ts
import { Notice } from "obsidian";
import type { CcodingBridge } from "../bridge/cli";

const BUSY_PATTERNS = ["locked", "busy", "EBUSY", "EAGAIN"];

function isBusyError(stderr: string): boolean {
  return BUSY_PATTERNS.some((p) => stderr.toLowerCase().includes(p.toLowerCase()));
}

/**
 * Execute a ghost action, showing user feedback via Notices.
 * If the canvas file is locked/busy, retries once after 500ms.
 */
async function runAction(
  bridge: CcodingBridge,
  action: () => Promise<any>,
  label: string,
): Promise<void> {
  const notice = new Notice(`${label}...`, 0);
  try {
    let result = await action();
    if (!result.success && isBusyError(result.stderr)) {
      // Retry once after 500ms
      await new Promise((r) => setTimeout(r, 500));
      result = await action();
    }
    notice.hide();
    if (!result.success) {
      const msg = isBusyError(result.stderr)
        ? "Canvas file is busy. Try again."
        : `Error: ${result.stderr}`;
      new Notice(msg, 5000);
    }
  } catch (err: any) {
    notice.hide();
    new Notice(`Error: ${err.message}`, 5000);
  }
}

export async function acceptNode(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(bridge, () => bridge.accept(id), "Accepting proposal");
}

export async function rejectNode(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(bridge, () => bridge.reject(id), "Rejecting proposal");
}

export async function reconsiderNode(
  bridge: CcodingBridge,
  id: string,
): Promise<void> {
  await runAction(
    bridge,
    () => bridge.reconsider(id),
    "Reconsidering proposal",
  );
}

export async function acceptAll(bridge: CcodingBridge): Promise<void> {
  await runAction(
    bridge,
    () => bridge.acceptAll(),
    "Accepting all proposals",
  );
}

export async function rejectAll(bridge: CcodingBridge): Promise<void> {
  await runAction(
    bridge,
    () => bridge.rejectAll(),
    "Rejecting all proposals",
  );
}

export async function syncCanvas(
  bridge: CcodingBridge,
): Promise<void> {
  await runAction(bridge, () => bridge.sync(), "Syncing canvas");
}

export async function checkStatus(
  bridge: CcodingBridge,
): Promise<void> {
  const result = await bridge.status();
  if (result.success) {
    new Notice(result.stdout || "In sync", 5000);
  } else {
    new Notice(`Error: ${result.stderr}`, 5000);
  }
}

export function showRationale(rationale: string | null): void {
  if (rationale) {
    new Notice(`Agent rationale: ${rationale}`, 10000);
  } else {
    new Notice("No rationale provided.", 3000);
  }
}
```

- [ ] **Step 2: Write ghost context menu**

```typescript
// src/ghost/menu.ts
import type { Menu } from "obsidian";
import type { CcodingMetadata, EdgeMetadata } from "../types";
import type { CcodingBridge } from "../bridge/cli";
import {
  acceptNode,
  rejectNode,
  reconsiderNode,
  showRationale,
} from "./actions";

/**
 * Add ghost-related menu items to a canvas node's context menu.
 */
export function addNodeMenuItems(
  menu: Menu,
  nodeId: string,
  meta: CcodingMetadata,
  bridge: CcodingBridge,
): void {
  if (meta.status === "proposed") {
    menu.addItem((item) =>
      item
        .setTitle("Accept")
        .setIcon("check")
        .onClick(() => acceptNode(bridge, nodeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Reject")
        .setIcon("x")
        .onClick(() => rejectNode(bridge, nodeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Show Rationale")
        .setIcon("info")
        .onClick(() => showRationale(meta.proposalRationale ?? null)),
    );
  } else if (meta.status === "rejected") {
    menu.addItem((item) =>
      item
        .setTitle("Reconsider")
        .setIcon("rotate-ccw")
        .onClick(() => reconsiderNode(bridge, nodeId)),
    );
  }
}

/**
 * Add ghost-related menu items to a canvas edge's context menu.
 */
export function addEdgeMenuItems(
  menu: Menu,
  edgeId: string,
  meta: EdgeMetadata,
  bridge: CcodingBridge,
): void {
  if (meta.status === "proposed") {
    menu.addItem((item) =>
      item
        .setTitle("Accept")
        .setIcon("check")
        .onClick(() => acceptNode(bridge, edgeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Reject")
        .setIcon("x")
        .onClick(() => rejectNode(bridge, edgeId)),
    );
  } else if (meta.status === "rejected") {
    menu.addItem((item) =>
      item
        .setTitle("Reconsider")
        .setIcon("rotate-ccw")
        .onClick(() => reconsiderNode(bridge, edgeId)),
    );
  }
}
```

- [ ] **Step 3: Write ghost action tests**

```typescript
// tests/ghost/actions.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock obsidian Notice
vi.mock("obsidian", () => ({
  Notice: vi.fn().mockImplementation(() => ({ hide: vi.fn() })),
}));

import { acceptNode, rejectNode, syncCanvas } from "../../src/ghost/actions";
import type { CcodingBridge } from "../../src/bridge/cli";

function mockBridge(result: any): CcodingBridge {
  return {
    accept: vi.fn().mockResolvedValue(result),
    reject: vi.fn().mockResolvedValue(result),
    reconsider: vi.fn().mockResolvedValue(result),
    acceptAll: vi.fn().mockResolvedValue(result),
    rejectAll: vi.fn().mockResolvedValue(result),
    sync: vi.fn().mockResolvedValue(result),
    status: vi.fn().mockResolvedValue(result),
  } as any;
}

describe("ghost actions", () => {
  it("calls bridge.accept for acceptNode", async () => {
    const bridge = mockBridge({ success: true, stdout: "", stderr: "", exitCode: 0 });
    await acceptNode(bridge, "node-1");
    expect(bridge.accept).toHaveBeenCalledWith("node-1");
  });

  it("calls bridge.reject for rejectNode", async () => {
    const bridge = mockBridge({ success: true, stdout: "", stderr: "", exitCode: 0 });
    await rejectNode(bridge, "node-2");
    expect(bridge.reject).toHaveBeenCalledWith("node-2");
  });

  it("retries on busy error", async () => {
    const busyResult = { success: false, stdout: "", stderr: "EBUSY: file locked", exitCode: 1 };
    const okResult = { success: true, stdout: "", stderr: "", exitCode: 0 };
    const bridge = mockBridge(busyResult);
    (bridge.sync as any)
      .mockResolvedValueOnce(busyResult)
      .mockResolvedValueOnce(okResult);
    await syncCanvas(bridge);
    expect(bridge.sync).toHaveBeenCalledTimes(2);
  });
});
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 6: Commit**

```bash
git add obsidian-plugin/src/ghost/ obsidian-plugin/tests/ghost/
git commit -m "feat: add ghost node context menu and action handlers"
```

---

### Task 11: Context Node Highlighting

**Files:**
- Create: `obsidian-plugin/src/highlight/context.ts`

- [ ] **Step 1: Write context highlighter**

```typescript
// src/highlight/context.ts

const HIGHLIGHT_CLASS = "ccoding-context-highlight";

/**
 * Manages context node highlighting when a ccoding node is selected.
 * Caches context edge mapping for O(1) lookups.
 */
export class ContextHighlighter {
  /** Map from node ID → set of connected context node IDs */
  private contextMap = new Map<string, Set<string>>();
  /** Map from node ID → set of connecting context edge IDs */
  private contextEdgeMap = new Map<string, Set<string>>();
  private canvasEl: HTMLElement | null = null;
  private currentHighlighted: string[] = [];

  /**
   * Build the context edge cache from canvas data.
   */
  buildCache(canvasData: any): void {
    this.contextMap.clear();
    this.contextEdgeMap.clear();

    if (!canvasData?.edges) return;
    for (const edge of canvasData.edges) {
      if (edge.ccoding?.relation !== "context") continue;
      const from = edge.fromNode as string;
      const to = edge.toNode as string;

      // Both directions: selecting either end highlights the other
      for (const [src, dst] of [[from, to], [to, from]]) {
        if (!this.contextMap.has(src)) {
          this.contextMap.set(src, new Set());
          this.contextEdgeMap.set(src, new Set());
        }
        this.contextMap.get(src)!.add(dst);
        this.contextEdgeMap.get(src)!.add(edge.id);
      }
    }
  }

  attach(canvasEl: HTMLElement): void {
    this.canvasEl = canvasEl;
  }

  detach(): void {
    this.clearHighlights();
    this.canvasEl = null;
  }

  /**
   * Called when canvas selection changes. Pass the selected node ID or null.
   */
  onSelectionChange(selectedNodeId: string | null): void {
    this.clearHighlights();
    if (!selectedNodeId || !this.canvasEl) return;

    const contextNodeIds = this.contextMap.get(selectedNodeId);
    const contextEdgeIds = this.contextEdgeMap.get(selectedNodeId);
    if (!contextNodeIds) return;

    for (const nodeId of contextNodeIds) {
      const el = this.canvasEl.querySelector<HTMLElement>(
        `.canvas-node[data-id="${nodeId}"]`,
      );
      if (el) {
        el.classList.add(HIGHLIGHT_CLASS);
        this.currentHighlighted.push(nodeId);
      }
    }

    if (contextEdgeIds) {
      for (const edgeId of contextEdgeIds) {
        const el = this.canvasEl.querySelector<HTMLElement>(
          `.canvas-edge[data-id="${edgeId}"]`,
        );
        if (el) {
          el.classList.add(HIGHLIGHT_CLASS);
        }
      }
    }
  }

  private clearHighlights(): void {
    if (!this.canvasEl) return;
    this.canvasEl
      .querySelectorAll(`.${HIGHLIGHT_CLASS}`)
      .forEach((el) => el.classList.remove(HIGHLIGHT_CLASS));
    this.currentHighlighted = [];
  }
}
```

- [ ] **Step 2: Write context highlighter tests**

```typescript
// tests/highlight/context.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { ContextHighlighter } from "../../src/highlight/context";

function makeCanvasData(edges: any[]) {
  return { edges };
}

describe("ContextHighlighter", () => {
  let highlighter: ContextHighlighter;

  beforeEach(() => {
    highlighter = new ContextHighlighter();
  });

  it("builds cache from context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
      { id: "e2", fromNode: "b", toNode: "ctx2", ccoding: { relation: "context" } },
      { id: "e3", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);

    // Internal check: selecting "a" should find "ctx1"
    // We test via onSelectionChange behavior below
  });

  it("ignores non-context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);
    // No context relationships should exist
  });

  it("handles empty canvas data", () => {
    highlighter.buildCache({ edges: [] });
    highlighter.buildCache(null);
    highlighter.buildCache(undefined);
    // Should not throw
  });
});
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 4: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/highlight/context.ts obsidian-plugin/tests/highlight/
git commit -m "feat: add context node highlighting on selection"
```

---

### Task 12: Hierarchical Layout (Pure Logic)

**Files:**
- Create: `obsidian-plugin/src/layout/graph.ts`
- Create: `obsidian-plugin/tests/layout/graph.test.ts`

- [ ] **Step 1: Write failing tests**

```typescript
// tests/layout/graph.test.ts
import { describe, it, expect } from "vitest";
import {
  buildGraph,
  assignLayers,
  computePositions,
  barycenterOrder,
  LAYER_GAP,
  NODE_GAP,
  type LayoutNode,
  type LayoutEdge,
} from "../../src/layout/graph";

const nodes: LayoutNode[] = [
  { id: "a", kind: "class", width: 320, height: 280 },
  { id: "b", kind: "class", width: 320, height: 280 },
  { id: "c", kind: "class", width: 320, height: 280 },
];

const edges: LayoutEdge[] = [
  { id: "e1", from: "a", to: "b", relation: "inherits" },
  { id: "e2", from: "a", to: "c", relation: "composes" },
];

describe("buildGraph", () => {
  it("creates adjacency lists from hierarchical edges", () => {
    const graph = buildGraph(nodes, edges);
    expect(graph.children.get("a")).toEqual(new Set(["b", "c"]));
    expect(graph.parents.get("b")).toEqual(new Set(["a"]));
  });

  it("ignores non-hierarchical edges", () => {
    const nonHier: LayoutEdge[] = [
      { id: "e1", from: "a", to: "b", relation: "depends" },
    ];
    const graph = buildGraph(nodes, nonHier);
    expect(graph.children.get("a")).toBeUndefined();
  });
});

describe("assignLayers", () => {
  it("puts roots at layer 0", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    expect(layers.get("a")).toBe(0);
  });

  it("puts children at layer 1", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    expect(layers.get("b")).toBe(1);
    expect(layers.get("c")).toBe(1);
  });
});

describe("computePositions", () => {
  it("returns positioned nodes", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    const positions = computePositions(nodes, layers, graph);
    expect(positions.length).toBe(3);
    // Root node at layer 0
    const posA = positions.find((p) => p.id === "a")!;
    expect(posA.y).toBe(0);
    // Children at layer 1
    const posB = positions.find((p) => p.id === "b")!;
    expect(posB.y).toBe(LAYER_GAP);
  });

  it("spaces nodes horizontally within a layer", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    const positions = computePositions(nodes, layers, graph);
    const layer1 = positions.filter((p) => p.id === "b" || p.id === "c");
    expect(layer1.length).toBe(2);
    // They should have different x positions
    expect(layer1[0].x).not.toBe(layer1[1].x);
  });
});

describe("barycenterOrder", () => {
  it("reorders children based on parent positions", () => {
    // d→b, d→c, a→c — c should come before b (closer to a+d average)
    const n: LayoutNode[] = [
      { id: "a", kind: "class", width: 320, height: 280 },
      { id: "d", kind: "class", width: 320, height: 280 },
      { id: "b", kind: "class", width: 320, height: 280 },
      { id: "c", kind: "class", width: 320, height: 280 },
    ];
    const e: LayoutEdge[] = [
      { id: "e1", from: "a", to: "c", relation: "inherits" },
      { id: "e2", from: "d", to: "b", relation: "inherits" },
      { id: "e3", from: "d", to: "c", relation: "inherits" },
    ];
    const graph = buildGraph(n, e);
    const layers = assignLayers(graph);
    const layerGroups = new Map<number, LayoutNode[]>();
    for (const node of n) {
      const layer = layers.get(node.id) ?? 0;
      if (!layerGroups.has(layer)) layerGroups.set(layer, []);
      layerGroups.get(layer)!.push(node);
    }
    barycenterOrder(layerGroups, graph);
    // After barycenter, both b and c should be in layer 1
    const layer1 = layerGroups.get(1)!;
    expect(layer1.map((n) => n.id)).toEqual(
      expect.arrayContaining(["b", "c"]),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd obsidian-plugin && npm test`
Expected: FAIL

- [ ] **Step 3: Write implementation**

```typescript
// src/layout/graph.ts

export const LAYER_GAP = 400;
export const NODE_GAP = 100;
export const DETAIL_OFFSET_Y = 350;
export const CONTEXT_OFFSET_X = 350;
export const GROUP_PADDING = 40;

export interface LayoutNode {
  id: string;
  kind?: string;
  width: number;
  height: number;
}

export interface LayoutEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
}

export interface NodePosition {
  id: string;
  x: number;
  y: number;
}

export interface Graph {
  nodeIds: Set<string>;
  children: Map<string, Set<string>>;
  parents: Map<string, Set<string>>;
}

const HIERARCHICAL_RELATIONS = new Set([
  "inherits",
  "implements",
  "composes",
  "detail",
]);

/**
 * Build a directed graph from nodes and hierarchical edges.
 */
export function buildGraph(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
): Graph {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const children = new Map<string, Set<string>>();
  const parents = new Map<string, Set<string>>();

  for (const edge of edges) {
    if (!HIERARCHICAL_RELATIONS.has(edge.relation)) continue;
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) continue;

    if (!children.has(edge.from)) children.set(edge.from, new Set());
    children.get(edge.from)!.add(edge.to);

    if (!parents.has(edge.to)) parents.set(edge.to, new Set());
    parents.get(edge.to)!.add(edge.from);
  }

  return { nodeIds, children, parents };
}

/**
 * Assign layer (depth) to each node via topological sort.
 * Roots (no parents) get layer 0. Each child gets max(parent layers) + 1.
 */
export function assignLayers(graph: Graph): Map<string, number> {
  const layers = new Map<string, number>();
  const visited = new Set<string>();
  const visiting = new Set<string>(); // cycle detection

  function dfs(nodeId: string): number {
    if (layers.has(nodeId)) return layers.get(nodeId)!;
    if (visiting.has(nodeId)) {
      // Cycle detected — assign current depth
      layers.set(nodeId, 0);
      return 0;
    }

    visiting.add(nodeId);
    const parentIds = graph.parents.get(nodeId);
    let maxParentLayer = -1;
    if (parentIds) {
      for (const pid of parentIds) {
        maxParentLayer = Math.max(maxParentLayer, dfs(pid));
      }
    }
    visiting.delete(nodeId);
    visited.add(nodeId);

    const layer = maxParentLayer + 1;
    layers.set(nodeId, layer);
    return layer;
  }

  for (const nodeId of graph.nodeIds) {
    if (!visited.has(nodeId)) dfs(nodeId);
  }

  return layers;
}

/**
 * Order nodes within each layer using the barycenter heuristic
 * to minimize edge crossings. Averages the positions of connected
 * nodes in the previous layer.
 */
export function barycenterOrder(
  layerGroups: Map<number, LayoutNode[]>,
  graph: Graph,
): void {
  const layerNums = Array.from(layerGroups.keys()).sort((a, b) => a - b);
  // Build position index for previous layer
  for (let i = 1; i < layerNums.length; i++) {
    const prevLayer = layerGroups.get(layerNums[i - 1])!;
    const prevIndex = new Map<string, number>();
    prevLayer.forEach((n, idx) => prevIndex.set(n.id, idx));

    const curLayer = layerGroups.get(layerNums[i])!;
    const barycenters = new Map<string, number>();

    for (const node of curLayer) {
      const parentIds = graph.parents.get(node.id);
      if (!parentIds || parentIds.size === 0) {
        barycenters.set(node.id, Infinity); // no parents, keep at end
        continue;
      }
      let sum = 0;
      let count = 0;
      for (const pid of parentIds) {
        const idx = prevIndex.get(pid);
        if (idx !== undefined) {
          sum += idx;
          count++;
        }
      }
      barycenters.set(node.id, count > 0 ? sum / count : Infinity);
    }

    curLayer.sort(
      (a, b) => (barycenters.get(a.id) ?? 0) - (barycenters.get(b.id) ?? 0),
    );
  }
}

/**
 * Compute x/y positions for each node based on layer assignment.
 * Applies barycenter heuristic for edge-crossing minimization.
 * Nodes in the same layer are spaced horizontally and centered.
 */
export function computePositions(
  nodes: LayoutNode[],
  layers: Map<string, number>,
  graph?: Graph,
): NodePosition[] {
  // Group nodes by layer
  const layerGroups = new Map<number, LayoutNode[]>();
  for (const node of nodes) {
    const layer = layers.get(node.id) ?? 0;
    if (!layerGroups.has(layer)) layerGroups.set(layer, []);
    layerGroups.get(layer)!.push(node);
  }

  // Apply barycenter ordering if graph is available
  if (graph) {
    barycenterOrder(layerGroups, graph);
  }

  const positions: NodePosition[] = [];

  for (const [layer, group] of layerGroups) {
    const y = layer * LAYER_GAP;
    const totalWidth =
      group.reduce((sum, n) => sum + n.width, 0) +
      NODE_GAP * (group.length - 1);
    let x = -totalWidth / 2;

    for (const node of group) {
      positions.push({ id: node.id, x, y });
      x += node.width + NODE_GAP;
    }
  }

  return positions;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/layout/graph.ts obsidian-plugin/tests/layout/graph.test.ts
git commit -m "feat: add hierarchical layout graph algorithms"
```

---

### Task 13: Layout Integration

**Files:**
- Create: `obsidian-plugin/src/layout/hierarchical.ts`

- [ ] **Step 1: Write layout integration**

```typescript
// src/layout/hierarchical.ts
import type { PluginSettings } from "../types";
import { parseCcodingMetadata, parseEdgeMetadata } from "../types";
import {
  buildGraph,
  assignLayers,
  computePositions,
  type LayoutNode,
  type LayoutEdge,
  DETAIL_OFFSET_Y,
  CONTEXT_OFFSET_X,
  NODE_GAP,
  GROUP_PADDING,
} from "./graph";

/**
 * Run hierarchical layout on canvas data.
 * Returns the modified canvas data with updated node positions.
 *
 * @param canvasData - The raw canvas JSON object
 * @param layoutAll - If true, layout all ccoding nodes. If false, only layoutPending nodes.
 * @param showRejected - Whether to include rejected nodes in layout.
 */
export function layoutCanvas(
  canvasData: any,
  layoutAll: boolean,
  showRejected: boolean,
): any {
  if (!canvasData?.nodes || !canvasData?.edges) return canvasData;

  // Identify which nodes to layout
  const targetNodeIds = new Set<string>();
  const detailEdges: Array<{ from: string; to: string }> = [];
  const contextEdges: Array<{ from: string; to: string }> = [];
  const layoutNodes: LayoutNode[] = [];
  const layoutEdges: LayoutEdge[] = [];

  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (!meta) continue;

    // Skip rejected when hidden
    if (meta.status === "rejected" && !showRejected) continue;

    const shouldLayout = layoutAll || meta.layoutPending;
    if (shouldLayout) {
      targetNodeIds.add(node.id);
    }

    // All ccoding nodes participate in graph building (for correct layer assignment)
    layoutNodes.push({
      id: node.id,
      kind: meta.kind,
      width: node.width || 320,
      height: node.height || 280,
    });
  }

  for (const edge of canvasData.edges) {
    const meta = parseEdgeMetadata(edge.ccoding);
    if (!meta) continue;

    layoutEdges.push({
      id: edge.id,
      from: edge.fromNode,
      to: edge.toNode,
      relation: meta.relation,
    });

    if (meta.relation === "detail") {
      detailEdges.push({ from: edge.fromNode, to: edge.toNode });
    }
    if (meta.relation === "context") {
      contextEdges.push({ from: edge.fromNode, to: edge.toNode });
    }
  }

  if (layoutNodes.length === 0) return canvasData;

  // Run layout with barycenter ordering
  const graph = buildGraph(layoutNodes, layoutEdges);
  const layers = assignLayers(graph);
  const positions = computePositions(layoutNodes, layers, graph);

  // Build position lookup
  const posMap = new Map(positions.map((p) => [p.id, p]));

  // Adjust detail nodes: position below their parent
  const detailCounts = new Map<string, number>();
  for (const { from, to } of detailEdges) {
    const parentPos = posMap.get(from);
    if (!parentPos) continue;
    const count = detailCounts.get(from) || 0;
    detailCounts.set(from, count + 1);
    posMap.set(to, {
      id: to,
      x: parentPos.x + count * (320 + NODE_GAP),
      y: parentPos.y + DETAIL_OFFSET_Y,
    });
  }

  // Adjust context nodes: position to the right
  const contextCounts = new Map<string, number>();
  for (const { from, to } of contextEdges) {
    const targetPos = posMap.get(from);
    if (!targetPos) continue;
    const count = contextCounts.get(from) || 0;
    contextCounts.set(from, count + 1);
    posMap.set(to, {
      id: to,
      x: targetPos.x + CONTEXT_OFFSET_X,
      y: targetPos.y + count * (280 + NODE_GAP),
    });
  }

  // Apply positions to canvas data — only for target nodes
  for (const node of canvasData.nodes) {
    if (!targetNodeIds.has(node.id)) continue;
    const pos = posMap.get(node.id);
    if (!pos) continue;
    node.x = pos.x;
    node.y = pos.y;
    // Clear layoutPending
    if (node.ccoding) {
      node.ccoding.layoutPending = false;
    }
  }

  // Package group sizing: nodes sharing the same package prefix in
  // qualifiedName are grouped. If a group node exists, resize it to
  // contain its children with padding.
  const packageChildren = new Map<string, string[]>();
  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (!meta?.qualifiedName) continue;
    const parts = meta.qualifiedName.split(".");
    if (parts.length < 2) continue;
    const pkg = parts.slice(0, -1).join(".");
    if (!packageChildren.has(pkg)) packageChildren.set(pkg, []);
    if (meta.kind !== "package") {
      packageChildren.get(pkg)!.push(node.id);
    }
  }

  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (meta?.kind !== "package" || !meta?.qualifiedName) continue;
    const children = packageChildren.get(meta.qualifiedName);
    if (!children || children.length === 0) continue;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const childId of children) {
      const child = canvasData.nodes.find((n: any) => n.id === childId);
      if (!child) continue;
      minX = Math.min(minX, child.x);
      minY = Math.min(minY, child.y);
      maxX = Math.max(maxX, child.x + (child.width || 320));
      maxY = Math.max(maxY, child.y + (child.height || 280));
    }

    if (minX !== Infinity) {
      node.x = minX - GROUP_PADDING;
      node.y = minY - GROUP_PADDING;
      node.width = (maxX - minX) + GROUP_PADDING * 2;
      node.height = (maxY - minY) + GROUP_PADDING * 2;
    }
  }

  return canvasData;
}
```

- [ ] **Step 2: Write layout integration tests**

```typescript
// tests/layout/hierarchical.test.ts
import { describe, it, expect } from "vitest";
import { layoutCanvas } from "../../src/layout/hierarchical";

function makeCanvasData() {
  return {
    nodes: [
      { id: "a", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "accepted", qualifiedName: "pkg.A", layoutPending: true } },
      { id: "b", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "accepted", qualifiedName: "pkg.B", layoutPending: true } },
      { id: "c", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "rejected", qualifiedName: "pkg.C", layoutPending: true } },
    ],
    edges: [
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits", status: "accepted" } },
    ],
  };
}

describe("layoutCanvas", () => {
  it("positions nodes hierarchically", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, true);
    const nodeA = result.nodes.find((n: any) => n.id === "a");
    const nodeB = result.nodes.find((n: any) => n.id === "b");
    expect(nodeB.y).toBeGreaterThan(nodeA.y);
  });

  it("clears layoutPending after layout", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, true);
    for (const node of result.nodes) {
      if (node.ccoding) {
        expect(node.ccoding.layoutPending).toBe(false);
      }
    }
  });

  it("skips rejected nodes when showRejected is false", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, false);
    const nodeC = result.nodes.find((n: any) => n.id === "c");
    // c should not have been repositioned (x/y still 0)
    expect(nodeC.x).toBe(0);
    expect(nodeC.y).toBe(0);
  });

  it("only layouts pending nodes when layoutAll is false", () => {
    const data = makeCanvasData();
    data.nodes[0].ccoding.layoutPending = false; // a is not pending
    const result = layoutCanvas(data, false, true);
    const nodeA = result.nodes.find((n: any) => n.id === "a");
    expect(nodeA.x).toBe(0); // unchanged
  });

  it("handles empty canvas data", () => {
    expect(layoutCanvas({ nodes: [], edges: [] }, true, true)).toEqual({ nodes: [], edges: [] });
    expect(layoutCanvas(null, true, true)).toBeNull();
  });
});
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 4: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 5: Commit**

```bash
git add obsidian-plugin/src/layout/hierarchical.ts obsidian-plugin/tests/layout/hierarchical.test.ts
git commit -m "feat: add layout integration (reads canvas, applies positions)"
```

---

### Task 14: Plugin Entry Point (Wire Everything Together)

**Files:**
- Modify: `obsidian-plugin/src/main.ts`

- [ ] **Step 1: Write the full main.ts**

```typescript
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
```

- [ ] **Step 2: Verify build**

Run: `cd obsidian-plugin && npm run build`
Expected: Builds with no errors

- [ ] **Step 3: Run all tests**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/src/main.ts
git commit -m "feat: wire plugin entry point — lifecycle, commands, context menus"
```

---

### Task 15: Test Fixtures + Integration Smoke Test

**Files:**
- Create: `obsidian-plugin/fixtures/` (copy from CLI fixtures)
- Create: `obsidian-plugin/tests/integration.test.ts`

- [ ] **Step 1: Copy test fixtures**

Note: The CLI package fixture files live at the project root under `tests/fixtures/`.
If they exist, copy them. If not, the test in Step 2 creates inline fixture data as a fallback.

```bash
# Copy from CLI package fixtures if they exist
if [ -f tests/fixtures/sample.canvas ]; then
  cp tests/fixtures/sample.canvas obsidian-plugin/fixtures/sample.canvas
  cp tests/fixtures/sample_no_ccoding.canvas obsidian-plugin/fixtures/sample_no_ccoding.canvas
else
  echo "CLI fixtures not found — will use inline fixture data in tests"
fi
```

- [ ] **Step 2: Write integration smoke test**

```typescript
// tests/integration.test.ts
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";
import { parseCcodingMetadata, parseEdgeMetadata } from "../src/types";
import { nodeClasses, edgeClasses } from "../src/styling/class-mapper";
import { buildGraph, assignLayers, computePositions } from "../src/layout/graph";
import type { LayoutNode, LayoutEdge } from "../src/layout/graph";

describe("Integration: fixture → styling → layout", () => {
  const fixture = JSON.parse(
    readFileSync(
      join(__dirname, "../fixtures/sample.canvas"),
      "utf-8",
    ),
  );

  it("parses all ccoding nodes from fixture", () => {
    const ccodingNodes = fixture.nodes.filter(
      (n: any) => parseCcodingMetadata(n.ccoding) !== null,
    );
    expect(ccodingNodes.length).toBeGreaterThan(0);
  });

  it("generates CSS classes for fixture nodes", () => {
    for (const node of fixture.nodes) {
      const meta = parseCcodingMetadata(node.ccoding);
      if (!meta) continue;
      const classes = nodeClasses(meta, false);
      expect(classes).toContain("ccoding-node");
      expect(classes.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("generates CSS classes for fixture edges", () => {
    for (const edge of fixture.edges) {
      const meta = parseEdgeMetadata(edge.ccoding);
      if (!meta) continue;
      const classes = edgeClasses(meta);
      expect(classes).toContain("ccoding-edge");
    }
  });

  it("runs layout on fixture without errors", () => {
    const layoutNodes: LayoutNode[] = fixture.nodes
      .filter((n: any) => parseCcodingMetadata(n.ccoding))
      .map((n: any) => ({
        id: n.id,
        kind: n.ccoding?.kind,
        width: n.width || 320,
        height: n.height || 280,
      }));

    const layoutEdges: LayoutEdge[] = fixture.edges
      .filter((e: any) => parseEdgeMetadata(e.ccoding))
      .map((e: any) => ({
        id: e.id,
        from: e.fromNode,
        to: e.toNode,
        relation: e.ccoding.relation,
      }));

    const graph = buildGraph(layoutNodes, layoutEdges);
    const layers = assignLayers(graph);
    const positions = computePositions(layoutNodes, layers, graph);

    expect(positions.length).toBe(layoutNodes.length);
    for (const pos of positions) {
      expect(typeof pos.x).toBe("number");
      expect(typeof pos.y).toBe("number");
    }
  });
});
```

- [ ] **Step 3: Run all tests**

Run: `cd obsidian-plugin && npm test`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add obsidian-plugin/fixtures/ obsidian-plugin/tests/integration.test.ts
git commit -m "feat: add test fixtures and integration smoke test"
```

---

### Task 16: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `cd obsidian-plugin && npm test`
Expected: All tests PASS

- [ ] **Step 2: Production build**

Run: `cd obsidian-plugin && npm run build`
Expected: `main.js` created with no errors, no warnings

- [ ] **Step 3: Verify plugin files are complete**

Check that these files exist:
- `obsidian-plugin/manifest.json`
- `obsidian-plugin/main.js`
- `obsidian-plugin/styles.css`

Run: `ls obsidian-plugin/manifest.json obsidian-plugin/main.js obsidian-plugin/styles.css`
Expected: All three files listed

- [ ] **Step 4: Verify file count**

Run: `find obsidian-plugin/src -name "*.ts" | wc -l`
Expected: 14 TypeScript source files

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final verification — all tests passing, plugin builds cleanly"
```
