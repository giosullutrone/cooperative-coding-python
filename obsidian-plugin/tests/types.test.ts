// tests/types.test.ts
import { describe, it, expect } from "vitest";
import {
  parseCcodingMetadata,
  parseEdgeMetadata,
  type CcodingMetadata,
} from "../src/types";

describe("parseCcodingMetadata", () => {
  it("parses full metadata", () => {
    const raw = {
      kind: "class",
      stereotype: "protocol",
      language: "python",
      source: "src/parser.py",
      qualifiedName: "parser.DocumentParser",
      status: "accepted",
      proposedBy: null,
      proposalRationale: null,
      layoutPending: false,
    };
    const meta = parseCcodingMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.kind).toBe("class");
    expect(meta!.stereotype).toBe("protocol");
    expect(meta!.status).toBe("accepted");
  });

  it("returns null for missing metadata", () => {
    expect(parseCcodingMetadata(undefined)).toBeNull();
    expect(parseCcodingMetadata(null)).toBeNull();
  });

  it("parses minimal ghost context node (status only, no kind)", () => {
    const raw = { status: "proposed", proposedBy: "agent" };
    const meta = parseCcodingMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.status).toBe("proposed");
    expect(meta!.kind).toBeUndefined();
  });
});

describe("parseEdgeMetadata", () => {
  it("parses edge metadata", () => {
    const raw = {
      relation: "inherits",
      status: "accepted",
      proposedBy: null,
      proposalRationale: null,
    };
    const meta = parseEdgeMetadata(raw);
    expect(meta).not.toBeNull();
    expect(meta!.relation).toBe("inherits");
  });
});
