// src/ghost/menu.ts
import type { Menu } from "obsidian";
import type { CcodingMetadata, EdgeMetadata } from "../types";
import type { CcodingBridge } from "../bridge/cli";
import {
  acceptNode,
  rejectNode,
  reconsiderNode,
  showRationale,
} from "./actions";

/**
 * Add ghost-related menu items to a canvas node's context menu.
 */
export function addNodeMenuItems(
  menu: Menu,
  nodeId: string,
  meta: CcodingMetadata,
  bridge: CcodingBridge,
): void {
  if (meta.status === "proposed") {
    menu.addItem((item) =>
      item
        .setTitle("Accept")
        .setIcon("check")
        .onClick(() => acceptNode(bridge, nodeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Reject")
        .setIcon("x")
        .onClick(() => rejectNode(bridge, nodeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Show Rationale")
        .setIcon("info")
        .onClick(() => showRationale(meta.proposalRationale ?? null)),
    );
  } else if (meta.status === "rejected") {
    menu.addItem((item) =>
      item
        .setTitle("Reconsider")
        .setIcon("rotate-ccw")
        .onClick(() => reconsiderNode(bridge, nodeId)),
    );
  }
}

/**
 * Add ghost-related menu items to a canvas edge's context menu.
 */
export function addEdgeMenuItems(
  menu: Menu,
  edgeId: string,
  meta: EdgeMetadata,
  bridge: CcodingBridge,
): void {
  if (meta.status === "proposed") {
    menu.addItem((item) =>
      item
        .setTitle("Accept")
        .setIcon("check")
        .onClick(() => acceptNode(bridge, edgeId)),
    );
    menu.addItem((item) =>
      item
        .setTitle("Reject")
        .setIcon("x")
        .onClick(() => rejectNode(bridge, edgeId)),
    );
  } else if (meta.status === "rejected") {
    menu.addItem((item) =>
      item
        .setTitle("Reconsider")
        .setIcon("rotate-ccw")
        .onClick(() => reconsiderNode(bridge, edgeId)),
    );
  }
}
