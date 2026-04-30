from __future__ import annotations

import asyncio
import json
import shlex
import socket
import subprocess
from dataclasses import dataclass

from sqlalchemy import select

from ..db import session_scope
from ..models import Node, NodeRole
from ..repositories import add_audit_event, get_user_by_username
from ..services.subscription_service import build_or_update_smart_subscription
from ..services.user_service import create_user_with_identity
from .models import OperationResult


@dataclass
class CmdResult:
    code: int
    out: str


def run_cmd(cmd: list[str], timeout: int = 1800) -> CmdResult:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return CmdResult(code=proc.returncode, out=out.strip())


def run_shell(cmd: str, timeout: int = 1800) -> CmdResult:
    return run_cmd(["bash", "-lc", cmd], timeout=timeout)


def _active_worker(session) -> Node:
    row = session.scalar(
        select(Node).where(
            Node.role == NodeRole.worker,
            Node.status.in_(["active", "degraded"]),
        )
    )
    if not row:
        raise RuntimeError("No active worker node found in control DB")
    return row


def create_or_recreate_user(username: str, display_name: str, actor: str) -> OperationResult:
    username = username.lstrip("@").strip().lower()
    if not username:
        return OperationResult(False, "Username is empty")

    with session_scope() as session:
        user = get_user_by_username(session, username)
        if not user:
            user = create_user_with_identity(session, username=username, display_name=display_name, actor=actor)
        else:
            user.display_name = display_name

        worker = _active_worker(session)
        if not worker or not worker.public_ip:
            raise RuntimeError("Worker node is missing public_ip")

        sub_url = build_or_update_smart_subscription(
            session=session,
            user=user,
            node_host=worker.public_ip,
            node_port=443,
            connect_uuid=str(user.connect_uuid),
        )

        add_audit_event(
            session,
            actor=actor,
            action="bot.user.provision",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"username": username, "worker": worker.name},
        )

    return OperationResult(True, f"User provisioned: @{username}", {"subscription_url": sub_url})


def delete_user_cascade(username: str, actor: str) -> OperationResult:
    username = username.lstrip("@").strip().lower()
    with session_scope() as session:
        user = get_user_by_username(session, username)
        if not user:
            return OperationResult(False, f"User not found: @{username}")
        user_id = str(user.id)
        session.delete(user)
        add_audit_event(
            session,
            actor=actor,
            action="bot.user.delete",
            entity_type="user",
            entity_id=user_id,
            metadata={"username": username},
        )
    return OperationResult(True, f"User deleted: @{username}")


async def dispatch_workflow_and_pick_run(gh, workflow_file: str, inputs: dict | None = None) -> int:
    gh.dispatch_workflow(workflow_file=workflow_file, ref="main", inputs=inputs or {})
    await asyncio.sleep(5)
    runs = gh.list_runs(workflow_file=workflow_file, branch="main", per_page=5)
    if not runs:
        raise RuntimeError(f"No runs found for {workflow_file} after dispatch")
    return int(runs[0]["id"])


def health_report(ssh_key_path: str = "") -> OperationResult:
    with session_scope() as session:
        nodes = list(session.scalars(select(Node).where(Node.role.in_([NodeRole.control, NodeRole.worker]))))

    if not nodes:
        return OperationResult(False, "No nodes in DB")

    report = []
    degraded = 0
    for node in nodes:
        node_data = {
            "name": node.name,
            "role": node.role.value,
            "status": node.status.value,
            "public_ip": node.public_ip or "",
            "tcp_22": "unknown",
            "tcp_443": "unknown",
            "cpu_load": "unknown",
            "mem_used_pct": "unknown",
            "disk_used_pct": "unknown",
            "net_rx_mb": "unknown",
            "net_tx_mb": "unknown",
            "services": "unknown",
        }

        if node.public_ip:
            for port in (22, 443):
                ok = _tcp_check(node.public_ip, port)
                node_data[f"tcp_{port}"] = "ok" if ok else "fail"

            if ssh_key_path:
                metrics = _ssh_metrics(node.public_ip, ssh_key_path)
                node_data.update(metrics)

        if node_data["tcp_22"] == "fail" or (node.role == NodeRole.worker and node_data["tcp_443"] == "fail"):
            degraded += 1

        report.append(node_data)

    summary = "All nodes look healthy"
    if degraded:
        summary = f"Detected {degraded} degraded node(s). Check SSH/VLESS reachability first."

    return OperationResult(True, summary, {"nodes": report})


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ssh_metrics(host: str, key_path: str) -> dict:
    # Collect lightweight metrics from host. If SSH is unavailable, keep unknowns.
    cmd = (
        "ssh -o BatchMode=yes -o StrictHostKeyChecking=no "
        f"-i {shlex.quote(key_path)} root@{shlex.quote(host)} "
        "\""
        "awk '{print $1}' /proc/loadavg; "
        "free | awk '/Mem:/ {printf \\\"%.2f\\\\n\\\", ($3/$2)*100}'; "
        "df -P / | awk 'NR==2 {gsub(/%/,\\\"\\\",$5); print $5}'; "
        "awk '/:/{if($1 !~ /lo:/){rx+=$2; tx+=$10}} END {printf \\\"%.2f\\\\n%.2f\\\\n\\\", rx/1024/1024, tx/1024/1024}' /proc/net/dev; "
        "if command -v systemctl >/dev/null 2>&1; then "
        "  (systemctl is-active xray 2>/dev/null || echo missing); "
        "  (systemctl is-active docker 2>/dev/null || echo missing); "
        "else echo missing; echo missing; fi"
        "\""
    )
    result = run_shell(cmd, timeout=20)
    if result.code != 0:
        return {"ssh": "fail"}
    lines = [x.strip() for x in result.out.splitlines() if x.strip()]
    if len(lines) < 7:
        return {"ssh": "ok"}
    return {
        "ssh": "ok",
        "cpu_load": lines[0],
        "mem_used_pct": lines[1],
        "disk_used_pct": lines[2],
        "net_rx_mb": lines[3],
        "net_tx_mb": lines[4],
        "services": f"xray={lines[5]},docker={lines[6]}",
    }


def format_health(result: OperationResult) -> str:
    if not result.ok:
        return f"Health failed: {result.message}"
    lines = [f"Health: {result.message}"]
    for n in result.details.get("nodes", []):
        lines.append(
            f"- {n['name']} ({n['role']}): status={n['status']} ip={n['public_ip']} "
            f"ssh={n['tcp_22']} vless443={n['tcp_443']} load={n['cpu_load']} mem={n['mem_used_pct']} "
            f"disk={n['disk_used_pct']} rxMB={n['net_rx_mb']} txMB={n['net_tx_mb']} svc[{n['services']}]"
        )
    return "\n".join(lines)


def build_incident_bundle(incident_id: str, operation: str, stage: str, error: str, extra: dict | None = None) -> dict:
    return {
        "incident_id": incident_id,
        "operation": operation,
        "stage": stage,
        "error": error,
        "extra": extra or {},
    }


def pretty_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=True, indent=2)
