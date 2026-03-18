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
