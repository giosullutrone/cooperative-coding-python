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
