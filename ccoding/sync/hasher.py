from __future__ import annotations
import hashlib

def content_hash(text: str) -> str:
    lines = text.splitlines()
    normalized = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        is_blank = stripped == ""
        if is_blank and prev_blank:
            continue
        normalized.append(stripped)
        prev_blank = is_blank
    while normalized and normalized[-1] == "":
        normalized.pop()
    content = "\n".join(normalized)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
