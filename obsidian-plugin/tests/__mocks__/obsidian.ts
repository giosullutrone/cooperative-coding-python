// Minimal Obsidian API mock for unit tests.
// Only stub what tests actually need — expand as required.

export class Plugin {
  app: any = {};
  manifest: any = {};
  async loadData(): Promise<any> { return {}; }
  async saveData(_data: any): Promise<void> {}
  addCommand(_cmd: any): any { return {}; }
  addStatusBarItem(): any { return { innerHTML: "", addClass() {}, createSpan() { return {}; } }; }
  registerEvent(_evt: any): void {}
  register(_fn: () => void): void {}
}

export class Notice {
  constructor(public message: string, public timeout?: number) {}
  hide(): void {}
}

export class Modal {
  app: any;
  contentEl: any = {
    empty() {},
    createEl() { return { createEl() { return {}; } }; },
  };
  constructor(app: any) { this.app = app; }
  open(): void {}
  close(): void {}
  onOpen(): void {}
  onClose(): void {}
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
  addTextArea(_cb: any): this { return this; }
  addToggle(_cb: any): this { return this; }
  addDropdown(_cb: any): this { return this; }
  addButton(_cb: any): this { return this; }
  addSeparator(): this { return this; }
}

/**
 * Obsidian's debounce function stub.
 */
export function debounce<T extends (...args: any[]) => any>(
  cb: T,
  _wait: number,
  _immediate?: boolean,
): T {
  return cb;
}
