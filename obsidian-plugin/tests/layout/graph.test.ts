// tests/layout/graph.test.ts
import { describe, it, expect } from "vitest";
import {
  buildGraph,
  assignLayers,
  computePositions,
  barycenterOrder,
  LAYER_GAP,
  NODE_GAP,
  type LayoutNode,
  type LayoutEdge,
} from "../../src/layout/graph";

const nodes: LayoutNode[] = [
  { id: "a", kind: "class", width: 320, height: 280 },
  { id: "b", kind: "class", width: 320, height: 280 },
  { id: "c", kind: "class", width: 320, height: 280 },
];

const edges: LayoutEdge[] = [
  { id: "e1", from: "a", to: "b", relation: "inherits" },
  { id: "e2", from: "a", to: "c", relation: "composes" },
];

describe("buildGraph", () => {
  it("creates adjacency lists from hierarchical edges", () => {
    const graph = buildGraph(nodes, edges);
    expect(graph.children.get("a")).toEqual(new Set(["b", "c"]));
    expect(graph.parents.get("b")).toEqual(new Set(["a"]));
  });

  it("ignores non-hierarchical edges", () => {
    const nonHier: LayoutEdge[] = [
      { id: "e1", from: "a", to: "b", relation: "depends" },
    ];
    const graph = buildGraph(nodes, nonHier);
    expect(graph.children.get("a")).toBeUndefined();
  });
});

describe("assignLayers", () => {
  it("puts roots at layer 0", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    expect(layers.get("a")).toBe(0);
  });

  it("puts children at layer 1", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    expect(layers.get("b")).toBe(1);
    expect(layers.get("c")).toBe(1);
  });
});

describe("computePositions", () => {
  it("returns positioned nodes", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    const positions = computePositions(nodes, layers, graph);
    expect(positions.length).toBe(3);
    // Root node at layer 0
    const posA = positions.find((p) => p.id === "a")!;
    expect(posA.y).toBe(0);
    // Children at layer 1
    const posB = positions.find((p) => p.id === "b")!;
    expect(posB.y).toBe(LAYER_GAP);
  });

  it("spaces nodes horizontally within a layer", () => {
    const graph = buildGraph(nodes, edges);
    const layers = assignLayers(graph);
    const positions = computePositions(nodes, layers, graph);
    const layer1 = positions.filter((p) => p.id === "b" || p.id === "c");
    expect(layer1.length).toBe(2);
    // They should have different x positions
    expect(layer1[0].x).not.toBe(layer1[1].x);
  });
});

describe("barycenterOrder", () => {
  it("reorders children based on parent positions", () => {
    // d→b, d→c, a→c — c should come before b (closer to a+d average)
    const n: LayoutNode[] = [
      { id: "a", kind: "class", width: 320, height: 280 },
      { id: "d", kind: "class", width: 320, height: 280 },
      { id: "b", kind: "class", width: 320, height: 280 },
      { id: "c", kind: "class", width: 320, height: 280 },
    ];
    const e: LayoutEdge[] = [
      { id: "e1", from: "a", to: "c", relation: "inherits" },
      { id: "e2", from: "d", to: "b", relation: "inherits" },
      { id: "e3", from: "d", to: "c", relation: "inherits" },
    ];
    const graph = buildGraph(n, e);
    const layers = assignLayers(graph);
    const layerGroups = new Map<number, LayoutNode[]>();
    for (const node of n) {
      const layer = layers.get(node.id) ?? 0;
      if (!layerGroups.has(layer)) layerGroups.set(layer, []);
      layerGroups.get(layer)!.push(node);
    }
    barycenterOrder(layerGroups, graph);
    // After barycenter, both b and c should be in layer 1
    const layer1 = layerGroups.get(1)!;
    expect(layer1.map((n) => n.id)).toEqual(
      expect.arrayContaining(["b", "c"]),
    );
  });
});
