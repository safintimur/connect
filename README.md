# Connect Infrastructure (Automation-First)

Repository model:
- Process 1: Control bootstrap.
- Process 2: Worker lifecycle.

No alternative deployment branches are documented in this repository.

## Core principles
- No manual server operations for normal lifecycle.
- Clear process boundaries: control process does not deploy worker runtime.
- User traffic profile is `smart` (RU direct, rest via VLESS + Reality).

## Prerequisites
1. Copy `.env.example` -> `.env`.
2. Fill required values: `BASE_SUBSCRIPTION_URL`, `REALITY_*`, `DATABASE_URL`.
3. Install dependencies: `pip install .`.
4. Run checks:
   - `make preflight`
   - `make check-env`

## Process 1: Control bootstrap
Command:
- `make control-bootstrap`

What it does:
1. Terraform apply (`infra/terraform`)
2. Inventory generation (`infra/ansible/inventory.generated.ini`)
3. Host hardening bootstrap
4. Deploy control runtime (API + DB container stack) on control host
5. Control metadata sync (executed through control runtime)

## Process 2: Worker lifecycle
Command:
- `make worker-deploy`

What it does:
1. Render worker Xray config from control metadata (on control host), fetch generated config
2. Apply worker runtime config/restart

Re-run after user/node config changes:
- `make reconcile-worker`

## CI workflows
- Control bootstrap: `.github/workflows/deploy.yml`
- Worker deploy: `.github/workflows/deploy-worker.yml`

## Required GitHub secrets
- `DIGITALOCEAN_TOKEN`
- `DO_SSH_KEY_FINGERPRINT`
- `DEPLOY_SSH_PRIVATE_KEY`
- `REALITY_PRIVATE_KEY`
- `REALITY_PUBLIC_KEY`
- `REALITY_SHORT_ID`

## Required GitHub variables
- `BASE_SUBSCRIPTION_URL`
- `ADMIN_CIDRS_JSON` (recommended, JSON array, example: `["203.0.113.10/32"]`)
- optional: `REALITY_SERVER_NAME`, `REALITY_DEST`

## User provisioning
- `connectctl user-provision-smart alice "Alice" connect-worker-uk-1`

## Baseline security applied automatically
- UFW default deny incoming + explicit allowlist
- SSH hardening (no password auth, root by key only)
- fail2ban for SSH
- sysctl network hardening
- unattended security upgrades
