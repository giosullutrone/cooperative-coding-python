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
  }
}
