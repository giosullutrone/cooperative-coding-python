// src/bridge/cli.ts
import { execFile as nodeExecFile } from "child_process";
import { existsSync } from "fs";
import { join, dirname } from "path";
import { AsyncQueue } from "./queue";
import type { CommandResult, PluginSettings } from "../types";

export interface ProposeOptions {
  kind: string;
  name: string;
  stereotype?: string;
  rationale?: string;
  language?: string;
}

export interface ProposeEdgeOptions {
  from: string;
  to: string;
  relation: string;
  label?: string;
  rationale?: string;
}

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

  restore(id: string): Promise<CommandResult> {
    return this.run(["restore", id]);
  }

  acceptAll(): Promise<CommandResult> {
    return this.run(["accept-all"]);
  }

  rejectAll(): Promise<CommandResult> {
    return this.run(["reject-all"]);
  }

  /** Propose a new ghost node. Returns the result with the new node ID in stdout. */
  propose(opts: ProposeOptions): Promise<CommandResult> {
    const args = ["propose", "--kind", opts.kind, "--name", opts.name];
    if (opts.stereotype) args.push("--stereotype", opts.stereotype);
    if (opts.rationale) args.push("--rationale", opts.rationale);
    if (opts.language) args.push("--language", opts.language);
    return this.run(args);
  }

  /** Propose a new ghost edge between two nodes. */
  proposeEdge(opts: ProposeEdgeOptions): Promise<CommandResult> {
    const args = [
      "propose-edge",
      "--from", opts.from,
      "--to", opts.to,
      "--relation", opts.relation,
    ];
    if (opts.label) args.push("--label", opts.label);
    if (opts.rationale) args.push("--rationale", opts.rationale);
    return this.run(args);
  }

  /** List all pending ghost proposals. */
  ghosts(): Promise<CommandResult> {
    return this.run(["ghosts"]);
  }

  /** Set the text content of a canvas node. */
  setText(nodeId: string, text: string): Promise<CommandResult> {
    return this.runWithStdin(["set-text", nodeId], text);
  }

  /** Show sync diff (dry-run). */
  diff(): Promise<CommandResult> {
    return this.run(["diff"]);
  }

  /** Show a node's content by qualified name. */
  show(qualifiedName: string): Promise<CommandResult> {
    return this.run(["show", qualifiedName]);
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

  /** Run a command with text piped to stdin. */
  private runWithStdin(args: string[], stdin: string): Promise<CommandResult> {
    return this.queue.enqueue(() =>
      this.execWithStdin(this.cliPath(), [...this.projectArgs(), ...args], stdin),
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

  private execWithStdin(cmd: string, args: string[], stdin: string): Promise<CommandResult> {
    return new Promise((resolve) => {
      const child = nodeExecFile(
        cmd,
        args,
        {
          timeout: this.settings.commandTimeout,
          cwd: this.getProjectRoot() || undefined,
        },
        (err, stdout, stderr) => {
          if (err) {
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
      child.stdin?.write(stdin);
      child.stdin?.end();
    });
  }
}
