// tests/highlight/context.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { ContextHighlighter } from "../../src/highlight/context";

function makeCanvasData(edges: any[]) {
  return { edges };
}

/** Create a mock canvas object with nodes and edges Maps. */
function mockCanvas(
  nodes: Array<{ id: string; nodeEl: any }>,
  edges: Array<{ id: string; lineGroupEl: any }>,
) {
  return {
    nodes: new Map(nodes.map((n) => [n.id, n])),
    edges: new Map(edges.map((e) => [e.id, e])),
  };
}

/** Create a mock DOM element with dataset support. */
function mockElement() {
  const dataset: Record<string, string | undefined> = {};
  return { dataset } as any;
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
    // Cache built without errors — tested via onSelectionChange below
  });

  it("highlights context nodes via data attributes on selection", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
    ]);
    highlighter.buildCache(data);

    const nodeA = { id: "a", nodeEl: mockElement() };
    const nodeCtx = { id: "ctx1", nodeEl: mockElement() };
    const edgeE1 = { id: "e1", lineGroupEl: mockElement() };
    const canvas = mockCanvas([nodeA, nodeCtx], [edgeE1]);
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBe("true");
    expect(edgeE1.lineGroupEl.dataset.ccodingContextHighlight).toBe("true");
  });

  it("clears highlights on selection change", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "ctx1", ccoding: { relation: "context" } },
    ]);
    highlighter.buildCache(data);

    const nodeCtx = { id: "ctx1", nodeEl: mockElement() };
    const canvas = mockCanvas(
      [{ id: "a", nodeEl: mockElement() }, nodeCtx],
      [{ id: "e1", lineGroupEl: mockElement() }],
    );
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBe("true");

    highlighter.onSelectionChange(null);
    expect(nodeCtx.nodeEl.dataset.ccodingContextHighlight).toBeUndefined();
  });

  it("ignores non-context edges", () => {
    const data = makeCanvasData([
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits" } },
    ]);
    highlighter.buildCache(data);

    const nodeB = { id: "b", nodeEl: mockElement() };
    const canvas = mockCanvas([{ id: "a", nodeEl: mockElement() }, nodeB], []);
    highlighter.attach(canvas);

    highlighter.onSelectionChange("a");
    expect(nodeB.nodeEl.dataset.ccodingContextHighlight).toBeUndefined();
  });

  it("handles empty canvas data", () => {
    highlighter.buildCache({ edges: [] });
    highlighter.buildCache(null);
    highlighter.buildCache(undefined);
    // Should not throw
  });
});
