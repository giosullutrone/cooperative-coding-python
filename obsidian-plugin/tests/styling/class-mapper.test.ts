// tests/styling/class-mapper.test.ts
import { describe, it, expect } from "vitest";
import { nodeClasses, edgeClasses } from "../../src/styling/class-mapper";
import type { CcodingMetadata, EdgeMetadata } from "../../src/types";

describe("nodeClasses", () => {
  it("accepted nodes get no extra visual styling", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-node");
    expect(classes).toContain("ccoding-accepted");
    expect(classes).not.toContain("ccoding-ghost");
  });

  it("adds ghost class for proposed nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "proposed" };
    const classes = nodeClasses(meta, false);
    expect(classes).toContain("ccoding-ghost");
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
  });
});

describe("edgeClasses", () => {
  it("accepted edges get base class only", () => {
    const meta: EdgeMetadata = { relation: "inherits", status: "accepted" };
    const classes = edgeClasses(meta);
    expect(classes).toContain("ccoding-edge");
    expect(classes).not.toContain("ccoding-ghost");
  });

  it("adds ghost class for proposed edges", () => {
    const meta: EdgeMetadata = { relation: "composes", status: "proposed" };
    const classes = edgeClasses(meta);
    expect(classes).toContain("ccoding-edge");
    expect(classes).toContain("ccoding-ghost");
  });
});
