// src/layout/graph.ts

export const LAYER_GAP = 400;
export const NODE_GAP = 100;
export const DETAIL_OFFSET_Y = 350;
export const CONTEXT_OFFSET_X = 350;
export const GROUP_PADDING = 40;

export interface LayoutNode {
  id: string;
  kind?: string;
  width: number;
  height: number;
}

export interface LayoutEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
}

export interface NodePosition {
  id: string;
  x: number;
  y: number;
}

export interface Graph {
  nodeIds: Set<string>;
  children: Map<string, Set<string>>;
  parents: Map<string, Set<string>>;
}

const HIERARCHICAL_RELATIONS = new Set([
  "inherits",
  "implements",
  "composes",
  "detail",
]);

/**
 * Build a directed graph from nodes and hierarchical edges.
 */
export function buildGraph(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
): Graph {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const children = new Map<string, Set<string>>();
  const parents = new Map<string, Set<string>>();

  for (const edge of edges) {
    if (!HIERARCHICAL_RELATIONS.has(edge.relation)) continue;
    if (!nodeIds.has(edge.from) || !nodeIds.has(edge.to)) continue;

    if (!children.has(edge.from)) children.set(edge.from, new Set());
    children.get(edge.from)!.add(edge.to);

    if (!parents.has(edge.to)) parents.set(edge.to, new Set());
    parents.get(edge.to)!.add(edge.from);
  }

  return { nodeIds, children, parents };
}

/**
 * Assign layer (depth) to each node via topological sort.
 * Roots (no parents) get layer 0. Each child gets max(parent layers) + 1.
 */
export function assignLayers(graph: Graph): Map<string, number> {
  const layers = new Map<string, number>();
  const visited = new Set<string>();
  const visiting = new Set<string>(); // cycle detection

  function dfs(nodeId: string): number {
    if (layers.has(nodeId)) return layers.get(nodeId)!;
    if (visiting.has(nodeId)) {
      // Cycle detected — assign current depth
      layers.set(nodeId, 0);
      return 0;
    }

    visiting.add(nodeId);
    const parentIds = graph.parents.get(nodeId);
    let maxParentLayer = -1;
    if (parentIds) {
      for (const pid of parentIds) {
        maxParentLayer = Math.max(maxParentLayer, dfs(pid));
      }
    }
    visiting.delete(nodeId);
    visited.add(nodeId);

    const layer = maxParentLayer + 1;
    layers.set(nodeId, layer);
    return layer;
  }

  for (const nodeId of graph.nodeIds) {
    if (!visited.has(nodeId)) dfs(nodeId);
  }

  return layers;
}

/**
 * Order nodes within each layer using the barycenter heuristic
 * to minimize edge crossings. Averages the positions of connected
 * nodes in the previous layer.
 */
export function barycenterOrder(
  layerGroups: Map<number, LayoutNode[]>,
  graph: Graph,
): void {
  const layerNums = Array.from(layerGroups.keys()).sort((a, b) => a - b);
  // Build position index for previous layer
  for (let i = 1; i < layerNums.length; i++) {
    const prevLayer = layerGroups.get(layerNums[i - 1])!;
    const prevIndex = new Map<string, number>();
    prevLayer.forEach((n, idx) => prevIndex.set(n.id, idx));

    const curLayer = layerGroups.get(layerNums[i])!;
    const barycenters = new Map<string, number>();

    for (const node of curLayer) {
      const parentIds = graph.parents.get(node.id);
      if (!parentIds || parentIds.size === 0) {
        barycenters.set(node.id, Infinity); // no parents, keep at end
        continue;
      }
      let sum = 0;
      let count = 0;
      for (const pid of parentIds) {
        const idx = prevIndex.get(pid);
        if (idx !== undefined) {
          sum += idx;
          count++;
        }
      }
      barycenters.set(node.id, count > 0 ? sum / count : Infinity);
    }

    curLayer.sort(
      (a, b) => (barycenters.get(a.id) ?? 0) - (barycenters.get(b.id) ?? 0),
    );
  }
}

/**
 * Compute x/y positions for each node based on layer assignment.
 * Applies barycenter heuristic for edge-crossing minimization.
 * Nodes in the same layer are spaced horizontally and centered.
 */
export function computePositions(
  nodes: LayoutNode[],
  layers: Map<string, number>,
  graph?: Graph,
): NodePosition[] {
  // Group nodes by layer
  const layerGroups = new Map<number, LayoutNode[]>();
  for (const node of nodes) {
    const layer = layers.get(node.id) ?? 0;
    if (!layerGroups.has(layer)) layerGroups.set(layer, []);
    layerGroups.get(layer)!.push(node);
  }

  // Apply barycenter ordering if graph is available
  if (graph) {
    barycenterOrder(layerGroups, graph);
  }

  const positions: NodePosition[] = [];

  for (const [layer, group] of layerGroups) {
    const y = layer * LAYER_GAP;
    const totalWidth =
      group.reduce((sum, n) => sum + n.width, 0) +
      NODE_GAP * (group.length - 1);
    let x = -totalWidth / 2;

    for (const node of group) {
      positions.push({ id: node.id, x, y });
      x += node.width + NODE_GAP;
    }
  }

  return positions;
}
