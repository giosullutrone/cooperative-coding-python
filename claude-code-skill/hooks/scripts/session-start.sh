#!/bin/bash
# Detect CooperativeCoding projects by walking up from CWD looking for .ccoding/.
# Output is injected into session context to nudge skill auto-triggering.

dir="$(pwd)"
while [ "$dir" != "/" ]; do
  if [ -d "$dir/.ccoding" ]; then
    echo "CooperativeCoding project detected. Use /ccoding or ask about the canvas design to get started."
    exit 0
  fi
  dir="$(dirname "$dir")"
done
