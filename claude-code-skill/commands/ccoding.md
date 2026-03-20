---
description: Work with CooperativeCoding canvases — create, design, implement, or review
argument-hint: "[create|design|implement|review]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

The user wants to work with a CooperativeCoding canvas.

**Mode requested:** $ARGUMENTS

If a mode was specified, route directly to the corresponding skill:
- `create` → follow the `cooperative-coding:create` skill
- `design` → follow the `cooperative-coding:design` skill
- `implement` → follow the `cooperative-coding:implement` skill
- `review` → follow the `cooperative-coding:review` skill

If no mode was specified, follow the `cooperative-coding` skill (it handles mode resolution via `last_mode` or asking the user).
