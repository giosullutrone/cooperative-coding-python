---
description: Work with CooperativeCoding canvases — create, design, implement, or review
argument-hint: "[create|design|implement|review]"
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

The user wants to work with a CooperativeCoding canvas.

**Mode requested:** $ARGUMENTS

If a mode was specified (create, design, implement, or review), proceed directly with that mode. If no mode was specified, check `.claude/cooperative-coding.local.md` for `last_mode` and suggest it, or ask which mode the user wants.

Follow the `cooperative-coding` skill instructions for the selected mode.
