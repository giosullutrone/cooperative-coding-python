// src/layout/hierarchical.ts
import { parseCcodingMetadata, parseEdgeMetadata } from "../types";
import {
  buildGraph,
  assignLayers,
  computePositions,
  type LayoutNode,
  type LayoutEdge,
  DETAIL_OFFSET_Y,
  CONTEXT_OFFSET_X,
  NODE_GAP,
  GROUP_PADDING,
} from "./graph";

/**
 * Run hierarchical layout on canvas data.
 * Returns the modified canvas data with updated node positions.
 *
 * @param canvasData - The raw canvas JSON object
 * @param layoutAll - If true, layout all ccoding nodes. If false, only layoutPending nodes.
 * @param showRejected - Whether to include rejected nodes in layout.
 */
export function layoutCanvas(
  canvasData: any,
  layoutAll: boolean,
  showRejected: boolean,
): any {
  if (!canvasData?.nodes || !canvasData?.edges) return canvasData;

  // Identify which nodes to layout
  const targetNodeIds = new Set<string>();
  const detailEdges: Array<{ from: string; to: string }> = [];
  const contextEdges: Array<{ from: string; to: string }> = [];
  const layoutNodes: LayoutNode[] = [];
  const layoutEdges: LayoutEdge[] = [];

  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (!meta) continue;

    // Skip rejected when hidden
    if (meta.status === "rejected" && !showRejected) continue;

    const shouldLayout = layoutAll || meta.layoutPending;
    if (shouldLayout) {
      targetNodeIds.add(node.id);
    }

    // All ccoding nodes participate in graph building (for correct layer assignment)
    layoutNodes.push({
      id: node.id,
      kind: meta.kind,
      width: node.width || 320,
      height: node.height || 280,
    });
  }

  for (const edge of canvasData.edges) {
    const meta = parseEdgeMetadata(edge.ccoding);
    if (!meta) continue;

    layoutEdges.push({
      id: edge.id,
      from: edge.fromNode,
      to: edge.toNode,
      relation: meta.relation,
    });

    if (meta.relation === "detail") {
      detailEdges.push({ from: edge.fromNode, to: edge.toNode });
    }
    if (meta.relation === "context") {
      contextEdges.push({ from: edge.fromNode, to: edge.toNode });
    }
  }

  if (layoutNodes.length === 0) return canvasData;

  // Run layout with barycenter ordering
  const graph = buildGraph(layoutNodes, layoutEdges);
  const layers = assignLayers(graph);
  const positions = computePositions(layoutNodes, layers, graph);

  // Build position lookup
  const posMap = new Map(positions.map((p) => [p.id, p]));

  // Adjust detail nodes: position below their parent
  const detailCounts = new Map<string, number>();
  for (const { from, to } of detailEdges) {
    const parentPos = posMap.get(from);
    if (!parentPos) continue;
    const count = detailCounts.get(from) || 0;
    detailCounts.set(from, count + 1);
    posMap.set(to, {
      id: to,
      x: parentPos.x + count * (320 + NODE_GAP),
      y: parentPos.y + DETAIL_OFFSET_Y,
    });
  }

  // Adjust context nodes: position to the right
  const contextCounts = new Map<string, number>();
  for (const { from, to } of contextEdges) {
    const targetPos = posMap.get(from);
    if (!targetPos) continue;
    const count = contextCounts.get(from) || 0;
    contextCounts.set(from, count + 1);
    posMap.set(to, {
      id: to,
      x: targetPos.x + CONTEXT_OFFSET_X,
      y: targetPos.y + count * (280 + NODE_GAP),
    });
  }

  // Apply positions to canvas data — only for target nodes
  for (const node of canvasData.nodes) {
    if (!targetNodeIds.has(node.id)) continue;
    const pos = posMap.get(node.id);
    if (!pos) continue;
    node.x = pos.x;
    node.y = pos.y;
    // Clear layoutPending
    if (node.ccoding) {
      node.ccoding.layoutPending = false;
    }
  }

  // Package group sizing: nodes sharing the same package prefix in
  // qualifiedName are grouped. If a group node exists, resize it to
  // contain its children with padding.
  const packageChildren = new Map<string, string[]>();
  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (!meta?.qualifiedName) continue;
    const parts = meta.qualifiedName.split(".");
    if (parts.length < 2) continue;
    const pkg = parts.slice(0, -1).join(".");
    if (!packageChildren.has(pkg)) packageChildren.set(pkg, []);
    if (meta.kind !== "package") {
      packageChildren.get(pkg)!.push(node.id);
    }
  }

  for (const node of canvasData.nodes) {
    const meta = parseCcodingMetadata(node.ccoding);
    if (meta?.kind !== "package" || !meta?.qualifiedName) continue;
    const children = packageChildren.get(meta.qualifiedName);
    if (!children || children.length === 0) continue;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const childId of children) {
      const child = canvasData.nodes.find((n: any) => n.id === childId);
      if (!child) continue;
      minX = Math.min(minX, child.x);
      minY = Math.min(minY, child.y);
      maxX = Math.max(maxX, child.x + (child.width || 320));
      maxY = Math.max(maxY, child.y + (child.height || 280));
    }

    if (minX !== Infinity) {
      node.x = minX - GROUP_PADDING;
      node.y = minY - GROUP_PADDING;
      node.width = (maxX - minX) + GROUP_PADDING * 2;
      node.height = (maxY - minY) + GROUP_PADDING * 2;
    }
  }

  return canvasData;
}
