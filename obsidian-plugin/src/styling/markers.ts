// src/styling/markers.ts

const MARKER_NS = "http://www.w3.org/2000/svg";
const DEFS_ID = "ccoding-marker-defs";

const MARKERS: Record<string, string> = {
  "ccoding-marker-inherits": `<marker id="ccoding-marker-inherits" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="none" stroke="#e2e8f0" stroke-width="1.5"/></marker>`,
  "ccoding-marker-implements": `<marker id="ccoding-marker-implements" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" markerHeight="10" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="none" stroke="#e2e8f0" stroke-width="1.5"/></marker>`,
  "ccoding-marker-composes": `<marker id="ccoding-marker-composes" viewBox="0 0 12 12" refX="0" refY="6" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M 0 6 L 6 0 L 12 6 L 6 12 z" fill="#8b5cf6"/></marker>`,
  "ccoding-marker-depends": `<marker id="ccoding-marker-depends" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10" fill="none" stroke="#64748b" stroke-width="1.5"/></marker>`,
  "ccoding-marker-calls": `<marker id="ccoding-marker-calls" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#f97316"/></marker>`,
  "ccoding-marker-detail": `<marker id="ccoding-marker-detail" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="8" markerHeight="8"><circle cx="5" cy="5" r="4" fill="#3b82f6"/></marker>`,
};

/**
 * Inject SVG marker definitions into the canvas SVG element.
 */
export function injectMarkers(svgEl: SVGElement): void {
  if (svgEl.querySelector(`#${DEFS_ID}`)) return;
  const defs = document.createElementNS(MARKER_NS, "defs");
  defs.id = DEFS_ID;
  defs.innerHTML = Object.values(MARKERS).join("\n");
  svgEl.prepend(defs);
}

/**
 * Remove injected SVG markers.
 */
export function removeMarkers(container: HTMLElement): void {
  container.querySelector(`#${DEFS_ID}`)?.remove();
}
