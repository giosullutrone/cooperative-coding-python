"""Google-style docstring section parser and renderer."""

from __future__ import annotations

import re
import textwrap

# Recognised section header pattern: one or two words followed by a colon.
# We match this after stripping leading whitespace from each line.
_SECTION_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z]*(?: [A-Za-z]+)?):\s*$")

# Canonical output order for render_docstring.
_RENDER_ORDER = [
    "summary",
    "responsibility",
    "collaborators",
    "pseudo code",
    "args",
    "returns",
    "raises",
    "attributes",
    "constraints",
]


def _detect_base_indent(lines: list[str]) -> str:
    """Return the common leading whitespace used for section headers.

    We look at the first non-empty, non-summary line that looks like a
    section header candidate to determine the indentation level used for
    headers throughout the docstring.
    """
    for line in lines:
        stripped = line.lstrip()
        if stripped and _SECTION_HEADER_RE.match(stripped):
            return line[: len(line) - len(stripped)]
    # Fall back: use the indentation of the first non-empty non-first line.
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            return line[: len(line) - len(stripped)]
    return ""


def parse_docstring(doc: str) -> dict[str, str]:
    """Parse a Google-style docstring into a dict of section → content.

    Args:
        doc: Raw docstring text (with or without surrounding quotes).

    Returns:
        Dict mapping lowercase section names to their content. Always
        contains at least the key ``"summary"``.
    """
    if not doc or not doc.strip():
        return {"summary": ""}

    lines = doc.splitlines()

    # ------------------------------------------------------------------ #
    # 1. Determine the base indentation (indentation of section headers). #
    # ------------------------------------------------------------------ #
    base_indent = _detect_base_indent(lines)
    base_indent_len = len(base_indent)

    # ------------------------------------------------------------------ #
    # 2. Collect the summary (first non-empty line, stripped).            #
    # ------------------------------------------------------------------ #
    summary = ""
    summary_line_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            summary = stripped
            summary_line_idx = i
            break

    result: dict[str, str] = {"summary": summary}

    if summary_line_idx == -1:
        return result

    # ------------------------------------------------------------------ #
    # 3. Walk remaining lines, grouping by section.                       #
    # ------------------------------------------------------------------ #
    current_section: str | None = None
    current_content_lines: list[str] = []

    def _flush(section: str, content_lines: list[str]) -> None:
        """Dedent and store accumulated content for *section*."""
        # Strip trailing blank lines.
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        text = textwrap.dedent("\n".join(content_lines)).strip()
        result[section] = text

    for line in lines[summary_line_idx + 1 :]:
        # Check whether this line is a section header at the base indent.
        # A header must start exactly at base_indent_len (not deeper).
        raw_indent = len(line) - len(line.lstrip())
        stripped = line.lstrip()

        is_header = (
            stripped  # non-empty
            and raw_indent == base_indent_len
            and _SECTION_HEADER_RE.match(stripped)
        )

        if is_header:
            # Save previous section.
            if current_section is not None:
                _flush(current_section, current_content_lines)
            current_section = _SECTION_HEADER_RE.match(stripped).group(1).lower()  # type: ignore[union-attr]
            current_content_lines = []
        else:
            if current_section is not None:
                current_content_lines.append(line)
            # Lines between summary and first section are ignored per spec.

    # Flush last section.
    if current_section is not None:
        _flush(current_section, current_content_lines)

    return result


def render_docstring(sections: dict[str, str], indent: int = 4) -> str:
    """Render a sections dict back to a Google-style docstring string.

    Args:
        sections: Mapping of lowercase section name → content text.
        indent: Number of spaces to use for indentation (default 4).

    Returns:
        Formatted docstring body (without surrounding triple-quotes).
    """
    pad = " " * indent
    parts: list[str] = []

    summary = sections.get("summary", "")
    parts.append(summary)

    # Emit sections in canonical order, then any extra keys not in the list.
    ordered_keys = list(_RENDER_ORDER)
    for key in sections:
        if key not in ordered_keys:
            ordered_keys.append(key)

    for key in ordered_keys:
        if key == "summary":
            continue
        content = sections.get(key, "")
        if not content:
            continue
        # Section header: capitalise each word.
        header = key.title() + ":"
        parts.append("")  # blank line before section
        parts.append(pad + header)
        # Indent each content line.
        for content_line in content.splitlines():
            parts.append(pad + pad + content_line if content_line.strip() else "")
    parts.append("")  # trailing newline after last section
    return "\n".join(parts)
