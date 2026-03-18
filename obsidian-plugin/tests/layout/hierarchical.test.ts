// tests/layout/hierarchical.test.ts
import { describe, it, expect } from "vitest";
import { layoutCanvas } from "../../src/layout/hierarchical";

function makeCanvasData() {
  return {
    nodes: [
      { id: "a", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "accepted", qualifiedName: "pkg.A", layoutPending: true } },
      { id: "b", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "accepted", qualifiedName: "pkg.B", layoutPending: true } },
      { id: "c", x: 0, y: 0, width: 320, height: 280, ccoding: { kind: "class", status: "rejected", qualifiedName: "pkg.C", layoutPending: true } },
    ],
    edges: [
      { id: "e1", fromNode: "a", toNode: "b", ccoding: { relation: "inherits", status: "accepted" } },
    ],
  };
}

describe("layoutCanvas", () => {
  it("positions nodes hierarchically", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, true);
    const nodeA = result.nodes.find((n: any) => n.id === "a");
    const nodeB = result.nodes.find((n: any) => n.id === "b");
    expect(nodeB.y).toBeGreaterThan(nodeA.y);
  });

  it("clears layoutPending after layout", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, true);
    for (const node of result.nodes) {
      if (node.ccoding) {
        expect(node.ccoding.layoutPending).toBe(false);
      }
    }
  });

  it("skips rejected nodes when showRejected is false", () => {
    const data = makeCanvasData();
    const result = layoutCanvas(data, true, false);
    const nodeC = result.nodes.find((n: any) => n.id === "c");
    // c should not have been repositioned (x/y still 0)
    expect(nodeC.x).toBe(0);
    expect(nodeC.y).toBe(0);
  });

  it("only layouts pending nodes when layoutAll is false", () => {
    const data = makeCanvasData();
    data.nodes[0].ccoding.layoutPending = false; // a is not pending
    const result = layoutCanvas(data, false, true);
    const nodeA = result.nodes.find((n: any) => n.id === "a");
    expect(nodeA.x).toBe(0); // unchanged
  });

  it("handles empty canvas data", () => {
    expect(layoutCanvas({ nodes: [], edges: [] }, true, true)).toEqual({ nodes: [], edges: [] });
    expect(layoutCanvas(null, true, true)).toBeNull();
  });
});
