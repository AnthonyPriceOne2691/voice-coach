#!/usr/bin/env bash
# stdin or $1 = command line; exit 1 to block
cmd="${1:-}"
if echo "$cmd" | grep -Eiq 'push[[:space:]].*(--force|-f).*[[:space:]]+(origin[[:space:]]+)?(main|master)\b'; then
  echo "blocked: force-push to main/master" >&2
  exit 1
fi
exit 0
