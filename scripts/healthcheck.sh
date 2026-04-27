#!/usr/bin/env bash
set -euo pipefail

NODES_FILE=""
TIMEOUT=5

while [[ $# -gt 0 ]]; do
  case "$1" in
    --nodes-file)
      NODES_FILE="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$NODES_FILE" ]]; then
  echo "Usage: $0 --nodes-file <file.json> [--timeout <seconds>]"
  exit 1
fi

if [[ ! -f "$NODES_FILE" ]]; then
  echo "Nodes file not found: $NODES_FILE"
  exit 1
fi

jq -c '.[]' "$NODES_FILE" | while read -r node; do
  enabled="$(echo "$node" | jq -r '.enabled')"
  if [[ "$enabled" != "true" ]]; then
    continue
  fi

  name="$(echo "$node" | jq -r '.name')"
  host="$(echo "$node" | jq -r '.host')"
  port="$(echo "$node" | jq -r '.port')"

  if nc -z -w "$TIMEOUT" "$host" "$port" >/dev/null 2>&1; then
    echo "[OK] $name reachable at $host:$port"
  else
    echo "[FAIL] $name unreachable at $host:$port"
  fi
done
