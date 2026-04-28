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
- Preflight checks: `.github/workflows/preflight.yml`
- Control bootstrap: `.github/workflows/deploy.yml`
- Worker deploy: `.github/workflows/deploy-worker.yml`

## Fast local test loop (no deploy)
Run this before push:
- `make preflight`
- `make ci-preflight`

`ci-preflight` includes:
- Python compile check
- Terraform `fmt -check` and `validate` (`init -backend=false`, no remote state changes)
- Ansible playbook syntax-check

Optional local GitHub Actions emulation with `act`:
- `act -W .github/workflows/preflight.yml -j lint-and-smoke`

## Required GitHub secrets
- `DIGITALOCEAN_TOKEN`
- `DO_SSH_KEY_FINGERPRINT`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DO_SPACES_ACCESS_KEY_ID`
- `DO_SPACES_SECRET_ACCESS_KEY`
- `REALITY_PRIVATE_KEY`
- `REALITY_PUBLIC_KEY`
- `REALITY_SHORT_ID`

## Required GitHub variables
- `BASE_SUBSCRIPTION_URL`
- `ADMIN_CIDRS_JSON` (JSON array, may be `[]`; must not include `0.0.0.0/0` or `::/0`)
- `TF_STATE_BUCKET` (recommended, default: `connect-space-bucket`)
- `TF_STATE_REGION` (recommended, default: `lon1`)
- `TF_STATE_KEY_PREFIX` (recommended, default: `connect-prod`)
- `PROJECT_NAME` (recommended, default: `connect-core`)
- `CONTROL_NODE_NAME` (recommended, default: `connect-control-1`)
- `CONTROL_NODE_REGION` (recommended, default: `lon1`)
- `CONTROL_NODE_SIZE` (recommended, default: `s-1vcpu-1gb`)
- `CONTROL_NODE_IMAGE` (recommended, default: `ubuntu-24-04-x64`)
- `WORKER_NODE_NAME` (recommended, default: `connect-worker-uk-1`)
- `WORKER_NODE_REGION` (recommended, default: `lon1`)
- `WORKER_NODE_SIZE` (recommended, default: `s-1vcpu-1gb`)
- `WORKER_NODE_IMAGE` (recommended, default: `ubuntu-24-04-x64`)
- `AUTO_RECREATE_INFRA` (`false` by default; set `true` only for forced replacement of matching droplets/firewalls)
- optional: `REALITY_SERVER_NAME`, `REALITY_DEST`

## Terraform state
- CI uses remote Terraform state in DigitalOcean Spaces via S3 backend config (`infra/terraform/backend.hcl`, generated in workflow runtime).
- State lock file is enabled (`use_lockfile = true`).
- Workflows are serialized with a single concurrency group (`connect-infra-prod`) to avoid parallel state mutation.
- SSH admin access is runner-only by default during CI deploy (firewall 22 allows only the current GitHub runner public IP for that run).

## User provisioning
- `connectctl user-provision-smart alice "Alice" connect-worker-uk-1`

## Baseline security applied automatically
- UFW default deny incoming + explicit allowlist
- SSH hardening (no password auth, root by key only)
- fail2ban for SSH
- sysctl network hardening
- unattended security upgrades
