// tests/styling/class-mapper.test.ts
import { describe, it, expect } from "vitest";
import { nodeClasses, edgeClasses } from "../../src/styling/class-mapper";
import type { CcodingMetadata, EdgeMetadata } from "../../src/types";

describe("nodeClasses", () => {
  it("maps class node to purple border", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-node-class");
    expect(classes).toContain("ccoding-accepted");
    expect(classes).not.toContain("ccoding-ghost");
  });

  it("maps method node to orange rounded", () => {
    const meta: CcodingMetadata = { kind: "method", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-method");
  });

  it("maps field node to blue rounded", () => {
    const meta: CcodingMetadata = { kind: "field", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-field");
  });

  it("maps package node", () => {
    const meta: CcodingMetadata = { kind: "package", status: "accepted" };
    expect(nodeClasses(meta, false)).toContain("ccoding-node-package");
  });

  it("adds ghost class for proposed nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "proposed" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-ghost");
    expect(classes).toContain("ccoding-node-class");
  });

  it("adds rejected class", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-rejected");
  });

  it("hides rejected when showRejected is false", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-rejected-hidden");
  });

  it("does not hide rejected when showRejected is true", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const classes = nodeClasses(meta, true);
    expect(classes).toContain("ccoding-rejected");
    expect(classes).not.toContain("ccoding-rejected-hidden");
  });

  it("adds stale class", () => {
    const meta: CcodingMetadata = { kind: "class", status: "stale" };
    expect(nodeClasses(meta, false)).toContain("ccoding-stale");
  });

  it("handles context ghost node (status only, no kind)", () => {
    const meta: CcodingMetadata = { status: "proposed", proposedBy: "agent" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-ghost");
    expect(classes).not.toContain("ccoding-node-class");
  });
});

describe("edgeClasses", () => {
  it("maps inherits edge", () => {
    const meta: EdgeMetadata = { relation: "inherits", status: "accepted" };
    expect(edgeClasses(meta)).toContain("ccoding-edge-inherits");
  });

  it("adds ghost class for proposed edges", () => {
    const meta: EdgeMetadata = { relation: "composes", status: "proposed" };
    const classes = edgeClasses(meta);
    expect(classes).toContain("ccoding-edge-composes");
    expect(classes).toContain("ccoding-ghost");
  });
});
