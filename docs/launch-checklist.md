# Launch Checklist

## Decisions
- [x] Deployment split by processes: control lifecycle and worker lifecycle.
- [x] No cascade in base profile.
- [x] Smart profile as base traffic profile.
- [x] Unique subscription per user.
- [x] Stack: Python + PostgreSQL + DigitalOcean + Terraform + Ansible.

## Implementation status
- [x] Control-plane package
- [x] PostgreSQL + Alembic migrations
- [x] DO provider adapter
- [x] VLESS + Reality subscription generation
- [x] Deployment workflows
- [x] Hardening baseline in bootstrap

## Pre-launch prerequisites
- [ ] Terraform available where deploy runs
- [ ] GitHub secrets configured
- [ ] REALITY keys configured in env and secrets
- [ ] Domain and DNS configured for control API/subscription URL

## Done when
- [ ] Infrastructure apply succeeds
- [ ] Bootstrap/configuration is idempotent
- [ ] Worker config validation passes
- [ ] Healthcheck marks worker healthy
- [ ] User receives working personal subscription
