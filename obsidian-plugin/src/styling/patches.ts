// src/styling/patches.ts
import type { CcodingMetadata } from "../types";

const PATCH_ATTR = "data-ccoding-patch";

/**
 * Apply DOM patches (badges, banners, footers) to a canvas node element.
 */
export function applyNodePatches(
  el: HTMLElement,
  meta: CcodingMetadata,
): void {
  // Stereotype badge
  if (meta.kind === "class" && meta.stereotype) {
    const badge = document.createElement("div");
    badge.className = "ccoding-stereotype-badge";
    badge.setAttribute(PATCH_ATTR, "stereotype");
    badge.textContent = `\u00AB${meta.stereotype}\u00BB`;
    el.prepend(badge);
  }

  // Proposed banner
  if (meta.status === "proposed") {
    const banner = document.createElement("div");
    banner.className = "ccoding-proposed-banner";
    banner.setAttribute(PATCH_ATTR, "proposed");
    banner.textContent = "PROPOSED";
    el.prepend(banner);
  }

  // Stale banner
  if (meta.status === "stale") {
    const banner = document.createElement("div");
    banner.className = "ccoding-stale-banner";
    banner.setAttribute(PATCH_ATTR, "stale");
    banner.textContent = "STALE";
    el.prepend(banner);
  }

  // Rationale footer
  if (meta.status === "proposed" && meta.proposalRationale) {
    const footer = document.createElement("div");
    footer.className = "ccoding-rationale-footer";
    footer.setAttribute(PATCH_ATTR, "rationale");
    const prefix = document.createElement("span");
    prefix.className = "ccoding-rationale-prefix";
    prefix.textContent = "\uD83D\uDCA1 Agent rationale: ";
    footer.appendChild(prefix);
    footer.appendChild(
      document.createTextNode(meta.proposalRationale),
    );
    el.appendChild(footer);
  }
}

/**
 * Remove all ccoding DOM patches from a container.
 */
export function removeAllPatches(container: HTMLElement): void {
  container
    .querySelectorAll(`[${PATCH_ATTR}]`)
    .forEach((el) => el.remove());
}
