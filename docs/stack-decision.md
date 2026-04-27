# Stack Decision

## Recommendation
- Terraform for infrastructure provisioning.
- Ansible for host bootstrap and configuration.
- Docker Compose for control services.
- Xray runtime managed by worker lifecycle automation.
- Kubernetes is not required for this project scope.

## Why
- Terraform gives stateful and repeatable infrastructure lifecycle.
- Ansible keeps server hardening/config idempotent.
- Compose is sufficient for current operational complexity.
- Kubernetes would increase operational overhead without clear payoff.

## Practical split
- Infra layer: Terraform
- Config layer: Ansible
- Service runtime: Compose (control), Xray runtime managed by worker process
