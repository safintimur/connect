# Operations Runbook (First 7 Days)

## Daily checks
- Verify node reachability (`scripts/healthcheck.sh`).
- Verify Xray service/container status.
- Check control API health.
- Check fail2ban banned IP spikes.

## Incident: worker degraded
1. Mark node degraded in metadata.
2. Route new users to fallback plan.
3. Collect logs.
4. If unresolved in 15 minutes, replace/restart worker.

## Replacement target
- Detection to isolation: < 5 min
- Full replacement and restore: < 15 min

## Rotation policy
- Rotate endpoint every 2-3 days or on quality signals.
- Keep fallback endpoint warmed and tested.
