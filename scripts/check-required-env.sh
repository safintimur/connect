#!/usr/bin/env bash
set -euo pipefail

required=(
  DATABASE_URL
  BASE_SUBSCRIPTION_URL
  REALITY_PRIVATE_KEY
  REALITY_PUBLIC_KEY
  REALITY_SHORT_ID
  REALITY_SERVER_NAME
  REALITY_DEST
)

missing=0
for var in "${required[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "[FAIL] missing env var: $var"
    missing=1
  else
    echo "[OK] $var"
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

for must_replace in REALITY_PRIVATE_KEY REALITY_PUBLIC_KEY; do
  value="${!must_replace:-}"
  if [[ "$value" == "REPLACE_ME" ]]; then
    echo "[FAIL] $must_replace still equals REPLACE_ME"
    exit 1
  fi
done

if [[ "${BASE_SUBSCRIPTION_URL:-}" == *"example.com"* ]]; then
  echo "[FAIL] BASE_SUBSCRIPTION_URL still points to example.com"
  exit 1
fi

echo "[OK] required env vars are set"
