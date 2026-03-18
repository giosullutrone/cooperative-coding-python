import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Debouncer } from "../../src/watcher/debounce";

describe("Debouncer", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("calls callback after delay", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(300);
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("resets timer on repeated triggers", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    vi.advanceTimersByTime(200);
    debouncer.trigger();
    vi.advanceTimersByTime(200);
    expect(cb).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("cancel prevents callback", () => {
    const cb = vi.fn();
    const debouncer = new Debouncer(cb, 300);
    debouncer.trigger();
    debouncer.cancel();
    vi.advanceTimersByTime(500);
    expect(cb).not.toHaveBeenCalled();
  });
});
