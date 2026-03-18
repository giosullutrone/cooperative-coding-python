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
