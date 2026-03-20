// src/canvas-helpers.ts
// Direct canvas data manipulation helpers — no CLI needed.

/** Generate a unique node ID. */
export function generateNodeId(): string {
  return `cc-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

/** Generate a unique edge ID. */
export function generateEdgeId(): string {
  return `ce-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

/** Build markdown text for a canvas node. */
export function buildNodeText(
  kind: string,
  name: string,
  description?: string,
): string {
  const heading = kind === "field" || kind === "method" ? `## ${name}` : `# ${name}`;
  if (description) return `${heading}\n---\n${description}`;
  return heading;
}

/** Default node dimensions by kind. */
export function defaultDimensions(kind: string): { width: number; height: number } {
  switch (kind) {
    case "field":
      return { width: 300, height: 120 };
    case "method":
      return { width: 380, height: 200 };
    case "class":
      return { width: 340, height: 200 };
    case "interface":
      return { width: 340, height: 160 };
    case "package":
      return { width: 260, height: 100 };
    case "module":
      return { width: 260, height: 100 };
    default:
      return { width: 320, height: 160 };
  }
}

export interface NewNodeData {
  kind: string;
  qualifiedName: string;
  status: string;
  stereotype?: string;
  language?: string;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface NewEdgeData {
  fromNode: string;
  toNode: string;
  relation: string;
  status: string;
  fromSide?: string;
  toSide?: string;
  label?: string;
}

/**
 * Add a new ccoding node to canvas data (mutates and returns data).
 * Returns the generated node ID.
 */
export function addNodeToCanvasData(
  data: any,
  node: NewNodeData,
): string {
  const id = generateNodeId();
  data.nodes = data.nodes || [];
  data.nodes.push({
    id,
    type: "text",
    text: node.text,
    ccoding: {
      kind: node.kind,
      qualifiedName: node.qualifiedName,
      status: node.status,
      ...(node.stereotype ? { stereotype: node.stereotype } : {}),
      ...(node.language ? { language: node.language } : {}),
      proposedBy: null,
      proposalRationale: null,
    },
    x: node.x,
    y: node.y,
    width: node.width,
    height: node.height,
  });
  return id;
}

/**
 * Add a new ccoding edge to canvas data (mutates and returns data).
 * Returns the generated edge ID.
 */
export function addEdgeToCanvasData(
  data: any,
  edge: NewEdgeData,
): string {
  const id = generateEdgeId();
  data.edges = data.edges || [];
  data.edges.push({
    id,
    ccoding: {
      relation: edge.relation,
      status: edge.status,
      proposedBy: null,
      proposalRationale: null,
    },
    fromNode: edge.fromNode,
    fromSide: edge.fromSide || "right",
    toNode: edge.toNode,
    toSide: edge.toSide || "left",
    ...(edge.label ? { label: edge.label } : {}),
  });
  return id;
}

/**
 * Find a node's position in canvas data to compute child placement.
 * Returns { x, y, width, height } or null.
 */
export function findNodePosition(
  data: any,
  nodeId: string,
): { x: number; y: number; width: number; height: number } | null {
  const node = (data.nodes || []).find((n: any) => n.id === nodeId);
  if (!node) return null;
  return { x: node.x, y: node.y, width: node.width, height: node.height };
}

/**
 * Compute position for a new child node relative to parent.
 * Places children to the right of the parent, stacked vertically.
 */
export function computeChildPosition(
  data: any,
  parentId: string,
  childWidth: number,
  childHeight: number,
): { x: number; y: number } {
  const parent = findNodePosition(data, parentId);
  if (!parent) return { x: 0, y: 0 };

  // Find existing children (nodes connected by detail edges from this parent)
  const detailEdges = (data.edges || []).filter(
    (e: any) => e.fromNode === parentId && e.ccoding?.relation === "detail",
  );
  const childIds = new Set(detailEdges.map((e: any) => e.toNode));

  // Find the bottom-most existing child
  let maxBottom = parent.y - parent.height / 2;
  for (const n of data.nodes || []) {
    if (childIds.has(n.id)) {
      const bottom = n.y + n.height;
      if (bottom > maxBottom) maxBottom = bottom;
    }
  }

  const gap = 20;
  return {
    x: parent.x + parent.width + 80,
    y: maxBottom + gap,
  };
}
