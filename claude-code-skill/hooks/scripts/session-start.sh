#!/bin/bash
# Detect CooperativeCoding projects by checking for .ccoding/ directory.
# Output is injected into session context to nudge skill auto-triggering.

if [ -d ".ccoding" ]; then
  echo "CooperativeCoding project detected. Use /ccoding or ask about the canvas design to get started."
fi
