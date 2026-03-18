import { Plugin } from "obsidian";

export default class CooperativeCodingPlugin extends Plugin {
  async onload() {
    console.log("CooperativeCoding plugin loaded");
  }

  onunload() {
    console.log("CooperativeCoding plugin unloaded");
  }
}
