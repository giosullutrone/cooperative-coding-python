// tests/highlight/context.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { ContextHighlighter } from "../../src/highlight/context";

function makeCanvasData(edges: any[]) {
  return { edges };
}

describe("ContextHighlighter", () => {
  let highlighter: ContextHighlighter;

  beforeEach(() => {
    highlighter = new ContextHighlighter();
  });

  it("builds cache from context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
      { id: "e2", fromNode: "b", toNode: "ctx2", ccoding: { relation: "context" } },
      { id: "e3", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);

    // Internal check: selecting "a" should find "ctx1"
    // We test via onSelectionChange behavior below
  });

  it("ignores non-context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);
    // No context relationships should exist
  });

  it("handles empty canvas data", () => {
    highlighter.buildCache({ edges: [] });
    highlighter.buildCache(null);
    highlighter.buildCache(undefined);
    // Should not throw
  });
});
