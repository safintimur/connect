# Launch Day Checklist (When VPS Is Purchased)

1. Provision control and worker VPS (UK).
2. Attach SSH keys, disable password login.
3. Run bootstrap playbook for both hosts.
4. Run Xray install playbook for worker host.
5. Deploy control-node panel/services.
6. Apply firewall rules and fail2ban config.
7. Validate ports and handshake.
8. Generate and publish subscription.
9. Run client test for main and fallback profile.
10. Enable continuous healthcheck.
