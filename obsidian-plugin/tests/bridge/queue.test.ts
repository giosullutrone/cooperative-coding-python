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
