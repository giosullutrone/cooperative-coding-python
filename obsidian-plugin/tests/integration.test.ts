// tests/integration.test.ts
import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { parseCcodingMetadata, parseEdgeMetadata } from "../src/types";
import { nodeClasses, edgeClasses } from "../src/styling/class-mapper";
import { buildGraph, assignLayers, computePositions } from "../src/layout/graph";
import type { LayoutNode, LayoutEdge } from "../src/layout/graph";

// Use fixture file if available, otherwise create inline fixture
const fixturePath = join(__dirname, "../fixtures/sample.canvas");
const fixture = existsSync(fixturePath)
  ? JSON.parse(readFileSync(fixturePath, "utf-8"))
  : {
      nodes: [
        { id: "n1", x: 0, y: 0, width: 320, height: 280, type: "text", text: "DocumentParser", ccoding: { kind: "class", stereotype: "protocol", status: "accepted", qualifiedName: "parser.DocumentParser", language: "python", source: "src/parser.py" } },
        { id: "n2", x: 0, y: 0, width: 320, height: 200, type: "text", text: "parse", ccoding: { kind: "method", status: "accepted", qualifiedName: "parser.DocumentParser.parse" } },
        { id: "n3", x: 0, y: 0, width: 320, height: 280, type: "text", text: "CacheManager", ccoding: { kind: "class", status: "proposed", proposedBy: "agent", proposalRationale: "Extract caching", layoutPending: true } },
      ],
      edges: [
        { id: "e1", fromNode: "n1", toNode: "n2", ccoding: { relation: "detail", status: "accepted" } },
        { id: "e2", fromNode: "n1", toNode: "n3", ccoding: { relation: "composes", status: "proposed" } },
      ],
    };

describe("Integration: fixture → styling → layout", () => {
  it("parses all ccoding nodes from fixture", () => {
    const ccodingNodes = fixture.nodes.filter(
      (n: any) => parseCcodingMetadata(n.ccoding) !== null,
    );
    expect(ccodingNodes.length).toBeGreaterThan(0);
  });

  it("generates CSS classes for fixture nodes", () => {
    for (const node of fixture.nodes) {
      const meta = parseCcodingMetadata(node.ccoding);
      if (!meta) continue;
      const classes = nodeClasses(meta, false);
      expect(classes).toContain("ccoding-node");
      expect(classes.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("generates CSS classes for fixture edges", () => {
    for (const edge of fixture.edges) {
      const meta = parseEdgeMetadata(edge.ccoding);
      if (!meta) continue;
      const classes = edgeClasses(meta);
      expect(classes).toContain("ccoding-edge");
    }
  });

  it("runs layout on fixture without errors", () => {
    const layoutNodes: LayoutNode[] = fixture.nodes
      .filter((n: any) => parseCcodingMetadata(n.ccoding))
      .map((n: any) => ({
        id: n.id,
        kind: n.ccoding?.kind,
        width: n.width || 320,
        height: n.height || 280,
      }));

    const layoutEdges: LayoutEdge[] = fixture.edges
      .filter((e: any) => parseEdgeMetadata(e.ccoding))
      .map((e: any) => ({
        id: e.id,
        from: e.fromNode,
        to: e.toNode,
        relation: e.ccoding.relation,
      }));

    const graph = buildGraph(layoutNodes, layoutEdges);
    const layers = assignLayers(graph);
    const positions = computePositions(layoutNodes, layers, graph);

    expect(positions.length).toBe(layoutNodes.length);
    for (const pos of positions) {
      expect(typeof pos.x).toBe("number");
      expect(typeof pos.y).toBe("number");
    }
  });
});
