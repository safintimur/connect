#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"
OUT_FILE="${1:-$ROOT_DIR/infra/ansible/inventory.generated.ini}"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required"
  exit 1
fi

json="$(terraform -chdir="$TF_DIR" output -json ansible_inventory)"

{
  echo "[control]"
  echo "$json" | jq -r '.control | to_entries[] | "\(.key) ansible_host=\(.value.ansible_host) ansible_user=\(.value.ansible_user)"'
  echo
  echo "[workers_uk]"
  echo "$json" | jq -r '.workers_uk | to_entries[] | "\(.key) ansible_host=\(.value.ansible_host) ansible_user=\(.value.ansible_user)"'
  echo
  echo "[all:vars]"
  echo "ansible_python_interpreter=/usr/bin/python3"
} > "$OUT_FILE"

echo "Generated inventory: $OUT_FILE"
