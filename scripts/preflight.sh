#!/usr/bin/env bash
set -euo pipefail

commands=(jq nc openssl)

for cmd in "${commands[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "[OK] $cmd found"
  else
    echo "[FAIL] $cmd missing"
    exit 1
  fi
done

echo "[OK] local preflight passed"
