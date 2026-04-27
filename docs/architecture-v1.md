# Architecture (Phase 1)

Date: 2026-04-27
Status: frozen for implementation

## Goals
- Maximum automation (no manual node bootstrap).
- Personal subscription per user (no shared UUID/link).
- Single traffic profile: `smart`.
- Two independent processes: control bootstrap and worker lifecycle.

## Process model
- Process 1 handles control bootstrap/lifecycle.
- Process 2 handles worker create/update rollout.
- Physical host placement is outside process definition.

## Routing profile
Profile: `smart`
- `geosite:ru -> direct`
- `geoip:ru -> direct`
- `geoip:private -> direct`
- `final -> proxy`

## Core components
1. `control-plane` (Python)
- user lifecycle
- node lifecycle
- subscription build/publish
- audit events

2. `database` (PostgreSQL)
- users, nodes, node_assignments, subscriptions, audit_events

3. `infra automation`
- Terraform for node lifecycle
- Ansible for hardening/config
- CI workflows for one-click operations

4. `health and rollout`
- periodic healthcheck
- config versioning
- subscription regeneration on changes

## Security and access
- One user = one UUID = one subscription link.
- Control-plane write operations are CLI/API automation only.
- Firewall and fail2ban on every host.

## Acceptance criteria
- User creation returns personal subscription URL.
- Node changes do not require manual SSH command sequences.
- Smart profile config is reproducible from templates.
- Config/user changes can be rolled out automatically.
