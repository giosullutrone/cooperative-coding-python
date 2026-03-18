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
