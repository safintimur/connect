#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="$ROOT_DIR/xray/templates"

if ! command -v xray >/dev/null 2>&1; then
  echo "[WARN] xray binary not found. Skipping strict validation."
  echo "[INFO] JSON syntax check only."
  for file in "$TEMPLATE_DIR"/*.json.tmpl; do
    sed 's/\${[A-Z0-9_]*}/PLACEHOLDER/g' "$file" | jq empty
    echo "[OK] JSON valid: $file"
  done
  exit 0
fi

for file in "$TEMPLATE_DIR"/*.json.tmpl; do
  temp_file="$(mktemp)"
  sed 's/\${[A-Z0-9_]*}/PLACEHOLDER/g' "$file" > "$temp_file"
  if xray -test -config "$temp_file" >/dev/null 2>&1; then
    echo "[OK] xray accepted: $file"
  else
    echo "[FAIL] xray rejected: $file"
    rm -f "$temp_file"
    exit 1
  fi
  rm -f "$temp_file"
done
