#!/bin/bash
file="$1"
if [ -f "$file" ]; then
  nl -ba "$file" | while read -r num text; do
    printf '%s|%s|%s\n' "$num" "ownerA" "2000-01-01"
  done
fi
