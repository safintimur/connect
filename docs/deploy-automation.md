# Deploy Automation Flow

## Process 1: Control bootstrap
Command:
- `make control-bootstrap`

Sequence:
1. Terraform apply (`infra/terraform`)
2. Inventory generation (`inventory.generated.ini`)
3. Host hardening bootstrap
4. Control runtime deploy on control host
5. Node metadata sync into control DB (via control runtime)

## Process 2: Worker lifecycle
Command:
- `make worker-deploy`

Sequence:
1. Render worker config on control host from control metadata
2. Fetch generated worker config to deploy controller
3. Deploy/restart worker runtime

After user changes:
- `make reconcile-worker`
