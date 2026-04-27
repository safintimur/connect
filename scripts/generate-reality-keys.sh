#!/usr/bin/env bash
set -euo pipefail

if ! command -v xray >/dev/null 2>&1; then
  echo "xray binary is required to generate Reality keys (xray x25519)."
  exit 1
fi

keys="$(xray x25519)"
private_key="$(echo "$keys" | awk -F': ' '/Private key/ {print $2}')"
public_key="$(echo "$keys" | awk -F': ' '/Public key/ {print $2}')"
short_id="$(openssl rand -hex 8)"

cat <<OUT
REALITY_PRIVATE_KEY=$private_key
REALITY_PUBLIC_KEY=$public_key
REALITY_SHORT_ID=$short_id
OUT
