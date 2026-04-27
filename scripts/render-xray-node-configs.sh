#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"
INVENTORY="$ROOT_DIR/infra/ansible/inventory.generated.ini"
PLAYBOOK="$ROOT_DIR/infra/ansible/playbooks/render_worker_config.yml"

for cmd in terraform jq ansible-playbook; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required"
    exit 1
  fi
done

worker_json="$(terraform -chdir="$TF_DIR" output -json worker_node)"
worker_name="$(echo "$worker_json" | jq -r '.name')"

ansible-playbook -i "$INVENTORY" "$PLAYBOOK" -e "worker_node_name=$worker_name"

echo "Rendered Xray config fetched to infra/generated/xray/$worker_name.json"
