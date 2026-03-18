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
