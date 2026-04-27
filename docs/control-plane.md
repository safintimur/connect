# Control Plane (Python + PostgreSQL)

## CLI commands
- `connectctl init-db`
- `connectctl user-add <username> <display_name>`
- `connectctl user-disable <username>`
- `connectctl node-register --name connect-worker-uk-1 --public-ip <ip>`
- `connectctl node-upsert <name> ...`
- `connectctl node-status <name> <status>`
- `connectctl subscription-build <username> <node_name>`
- `connectctl user-provision-smart <username> <display_name> <node_name>`
- `connectctl xray-render-node-config <node_name> --output <path>`
- `connectctl do-create-worker <name>`

## API endpoints
- `GET /healthz`
- `GET /s/{token}`
