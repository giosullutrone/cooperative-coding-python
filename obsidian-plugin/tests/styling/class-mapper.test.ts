// tests/styling/class-mapper.test.ts
import { describe, it, expect } from "vitest";
import { nodeAttributes, edgeAttributes } from "../../src/styling/class-mapper";
import type { CcodingMetadata, EdgeMetadata } from "../../src/types";

describe("nodeAttributes", () => {
  it("returns kind and status for accepted nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-kind"]).toBe("class");
    expect(attrs["data-ccoding-status"]).toBe("accepted");
    expect(attrs["data-ccoding-rejected-hidden"]).toBeUndefined();
  });

  it("returns status for proposed nodes", () => {
    const meta: CcodingMetadata = { kind: "class", status: "proposed" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("proposed");
  });

  it("returns rejected-hidden when hideRejected is true", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const attrs = nodeAttributes(meta, true);
    expect(attrs["data-ccoding-status"]).toBe("rejected");
    expect(attrs["data-ccoding-rejected-hidden"]).toBe("true");
  });

  it("does not return rejected-hidden when hideRejected is false", () => {
    const meta: CcodingMetadata = { kind: "class", status: "rejected" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("rejected");
    expect(attrs["data-ccoding-rejected-hidden"]).toBeUndefined();
  });

  it("returns stale status", () => {
    const meta: CcodingMetadata = { kind: "class", status: "stale" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("stale");
  });

  it("returns stereotype when present", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted", stereotype: "abstract" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-stereotype"]).toBe("abstract");
  });

  it("omits stereotype when not present", () => {
    const meta: CcodingMetadata = { kind: "class", status: "accepted" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-stereotype"]).toBeUndefined();
  });

  it("handles nodes with status only (no kind)", () => {
    const meta: CcodingMetadata = { status: "proposed" };
    const attrs = nodeAttributes(meta, false);
    expect(attrs["data-ccoding-status"]).toBe("proposed");
    expect(attrs["data-ccoding-kind"]).toBeUndefined();
  });
});

describe("edgeAttributes", () => {
  it("returns relation and status for accepted edges", () => {
    const meta: EdgeMetadata = { relation: "inherits", status: "accepted" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("inherits");
    expect(attrs["data-ccoding-status"]).toBe("accepted");
  });

  it("returns proposed status", () => {
    const meta: EdgeMetadata = { relation: "composes", status: "proposed" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("composes");
    expect(attrs["data-ccoding-status"]).toBe("proposed");
  });

  it("omits status when undefined", () => {
    const meta: EdgeMetadata = { relation: "context" };
    const attrs = edgeAttributes(meta);
    expect(attrs["data-ccoding-relation"]).toBe("context");
    expect(attrs["data-ccoding-status"]).toBeUndefined();
  });
});
