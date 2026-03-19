// tests/ghost/actions.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock obsidian Notice
vi.mock("obsidian", () => ({
  Notice: vi.fn().mockImplementation(() => ({ hide: vi.fn() })),
}));

import { acceptElement, rejectElement, syncCanvas } from "../../src/ghost/actions";
import type { CcodingBridge } from "../../src/bridge/cli";

function mockBridge(result: any): CcodingBridge {
  return {
    accept: vi.fn().mockResolvedValue(result),
    reject: vi.fn().mockResolvedValue(result),
    reconsider: vi.fn().mockResolvedValue(result),
    acceptAll: vi.fn().mockResolvedValue(result),
    rejectAll: vi.fn().mockResolvedValue(result),
    sync: vi.fn().mockResolvedValue(result),
    status: vi.fn().mockResolvedValue(result),
  } as any;
}

describe("ghost actions", () => {
  it("calls bridge.accept for acceptElement", async () => {
    const bridge = mockBridge({ success: true, stdout: "", stderr: "", exitCode: 0 });
    await acceptElement(bridge, "node-1");
    expect(bridge.accept).toHaveBeenCalledWith("node-1");
  });

  it("calls bridge.reject for rejectElement", async () => {
    const bridge = mockBridge({ success: true, stdout: "", stderr: "", exitCode: 0 });
    await rejectElement(bridge, "node-2");
    expect(bridge.reject).toHaveBeenCalledWith("node-2");
  });

  it("works for edge IDs too", async () => {
    const bridge = mockBridge({ success: true, stdout: "", stderr: "", exitCode: 0 });
    await acceptElement(bridge, "edge-abc");
    expect(bridge.accept).toHaveBeenCalledWith("edge-abc");
  });

  it("retries on busy error", async () => {
    const busyResult = { success: false, stdout: "", stderr: "EBUSY: file locked", exitCode: 1 };
    const okResult = { success: true, stdout: "", stderr: "", exitCode: 0 };
    const bridge = mockBridge(busyResult);
    (bridge.sync as any)
      .mockResolvedValueOnce(busyResult)
      .mockResolvedValueOnce(okResult);
    await syncCanvas(bridge);
    expect(bridge.sync).toHaveBeenCalledTimes(2);
  });
});
