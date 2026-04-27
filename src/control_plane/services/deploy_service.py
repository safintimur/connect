from __future__ import annotations

import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def terraform_apply(terraform_dir: Path) -> None:
    run_cmd(["terraform", "init", "-input=false"], cwd=terraform_dir)
    run_cmd(["terraform", "apply", "-auto-approve", "-input=false"], cwd=terraform_dir)


def ansible_bootstrap(ansible_dir: Path, inventory: str) -> None:
    run_cmd(
        [
            "ansible-playbook",
            "-i",
            inventory,
            "playbooks/bootstrap.yml",
        ],
        cwd=ansible_dir,
    )


def ansible_install_xray(ansible_dir: Path, inventory: str) -> None:
    run_cmd(
        [
            "ansible-playbook",
            "-i",
            inventory,
            "playbooks/install_xray.yml",
        ],
        cwd=ansible_dir,
    )
