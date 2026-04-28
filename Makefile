.PHONY: preflight check-env validate healthcheck compile initdb tf-init tf-plan tf-apply tf-validate tf-fmt-check ansible-syntax ci-preflight render-inventory deploy-control sync-nodes render-xray ansible-bootstrap ansible-xray control-bootstrap worker-deploy reconcile-worker

preflight:
	bash scripts/preflight.sh

check-env:
	bash scripts/check-required-env.sh

validate:
	bash scripts/validate-xray-configs.sh

healthcheck:
	bash scripts/healthcheck.sh --nodes-file nodes/nodes.example.json

compile:
	python3 -m compileall src/control_plane

tf-fmt-check:
	terraform -chdir=infra/terraform fmt -check -recursive

tf-validate:
	terraform -chdir=infra/terraform init -backend=false
	terraform -chdir=infra/terraform validate

ansible-syntax:
	ansible-playbook --syntax-check -i localhost, infra/ansible/playbooks/bootstrap.yml
	ansible-playbook --syntax-check -i localhost, infra/ansible/playbooks/deploy_control.yml
	ansible-playbook --syntax-check -i localhost, infra/ansible/playbooks/install_xray.yml
	ansible-playbook --syntax-check -i localhost, infra/ansible/playbooks/sync_nodes_control.yml

ci-preflight: compile tf-fmt-check tf-validate ansible-syntax

initdb:
	connectctl init-db

tf-init:
	@if [ -n "$$TF_BACKEND_CONFIG_FILE" ]; then \
		terraform -chdir=infra/terraform init -backend-config=$$TF_BACKEND_CONFIG_FILE; \
	else \
		terraform -chdir=infra/terraform init; \
	fi

tf-plan: tf-init
	terraform -chdir=infra/terraform plan -var-file=terraform.tfvars

tf-apply: tf-init
	terraform -chdir=infra/terraform apply -auto-approve -var-file=terraform.tfvars

render-inventory:
	bash scripts/render-ansible-inventory.sh

deploy-control:
	ansible-playbook -i infra/ansible/inventory.generated.ini infra/ansible/playbooks/deploy_control.yml

render-xray:
	bash scripts/render-xray-node-configs.sh

sync-nodes:
	bash scripts/sync-nodes-from-terraform.sh

ansible-bootstrap:
	ansible-playbook -i infra/ansible/inventory.generated.ini infra/ansible/playbooks/bootstrap.yml

ansible-xray:
	ansible-playbook -i infra/ansible/inventory.generated.ini infra/ansible/playbooks/install_xray.yml

control-bootstrap: check-env tf-apply render-inventory ansible-bootstrap deploy-control sync-nodes

worker-deploy: render-xray ansible-xray

reconcile-worker: worker-deploy
