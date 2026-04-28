#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="$ROOT_DIR/infra/terraform"
INVENTORY="$ROOT_DIR/infra/ansible/inventory.generated.ini"
PLAYBOOK="$ROOT_DIR/infra/ansible/playbooks/sync_nodes_control.yml"

for cmd in terraform jq ansible-playbook; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required"
    exit 1
  fi
done

control_json="$(terraform -chdir="$TF_DIR" output -json control_node)"
worker_json="$(terraform -chdir="$TF_DIR" output -json worker_node 2>/dev/null || echo null)"

control_name="$(echo "$control_json" | jq -r '.name')"
control_id="$(echo "$control_json" | jq -r '.id | tostring')"
control_ip="$(echo "$control_json" | jq -r '.public_ip')"

worker_name="$(echo "$worker_json" | jq -r '.name // empty')"
worker_id="$(echo "$worker_json" | jq -r '.id // empty | tostring')"
worker_ip="$(echo "$worker_json" | jq -r '.public_ip // empty')"

worker_sync_enabled="false"
if [[ "$worker_json" != "null" ]]; then
  worker_sync_enabled="true"
fi

ansible-playbook -i "$INVENTORY" "$PLAYBOOK" \
  -e "control_node_name=$control_name" \
  -e "control_provider_id=$control_id" \
  -e "control_public_ip=$control_ip" \
  -e "worker_sync_enabled=$worker_sync_enabled" \
  -e "worker_node_name=$worker_name" \
  -e "worker_provider_id=$worker_id" \
  -e "worker_public_ip=$worker_ip"
