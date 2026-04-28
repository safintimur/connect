#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _api_request(token: str, method: str, path: str) -> dict | None:
    url = f"https://api.digitalocean.com{path}"
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as err:
        payload = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DO API {method} {path} failed: {err.code} {payload}") from err


def _list_droplets(token: str) -> list[dict]:
    droplets: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"page": page, "per_page": 200})
        data = _api_request(token, "GET", f"/v2/droplets?{query}") or {}
        batch = data.get("droplets", [])
        droplets.extend(batch)
        if len(batch) < 200:
            break
        page += 1
    return droplets


def _list_firewalls(token: str) -> list[dict]:
    firewalls: list[dict] = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"page": page, "per_page": 200})
        data = _api_request(token, "GET", f"/v2/firewalls?{query}") or {}
        batch = data.get("firewalls", [])
        firewalls.extend(batch)
        if len(batch) < 200:
            break
        page += 1
    return firewalls


def main() -> int:
    token = os.getenv("DIGITALOCEAN_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DIGITALOCEAN_TOKEN is required")

    project_name = os.getenv("PROJECT_NAME", "connect-core").strip()
    control_name = os.getenv("CONTROL_NODE_NAME", "connect-control-1").strip()
    worker_name = os.getenv("WORKER_NODE_NAME", "connect-worker-uk-1").strip()
    create_control = _bool_env("CREATE_CONTROL", True)
    create_worker = _bool_env("CREATE_WORKER", True)

    target_node_names: set[str] = set()
    if create_control:
        target_node_names.add(control_name)
    if create_worker:
        target_node_names.add(worker_name)

    target_firewall_names: set[str] = set()
    if create_control:
        target_firewall_names.add(f"{project_name}-control-fw")
    if create_worker:
        target_firewall_names.add(f"{project_name}-worker-uk-fw")

    print(f"[cleanup] project_name={project_name}")
    print(f"[cleanup] target_node_names={sorted(target_node_names)}")
    print(f"[cleanup] target_firewall_names={sorted(target_firewall_names)}")

    droplets = _list_droplets(token)
    deleted_droplet_ids: list[int] = []
    for droplet in droplets:
        name = droplet.get("name", "")
        if name not in target_node_names:
            continue
        droplet_id = int(droplet["id"])
        print(f"[cleanup] delete droplet id={droplet_id} name={name}")
        _api_request(token, "DELETE", f"/v2/droplets/{droplet_id}")
        deleted_droplet_ids.append(droplet_id)

    if deleted_droplet_ids:
        timeout_s = 240
        poll_s = 5
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            active = {
                int(d["id"])
                for d in _list_droplets(token)
                if int(d["id"]) in deleted_droplet_ids
            }
            if not active:
                break
            print(f"[cleanup] waiting for droplet deletion: {sorted(active)}")
            time.sleep(poll_s)
        else:
            raise RuntimeError("Timeout waiting for droplet deletion")

    firewalls = _list_firewalls(token)
    for fw in firewalls:
        name = fw.get("name", "")
        if name not in target_firewall_names:
            continue
        fw_id = fw["id"]
        print(f"[cleanup] delete firewall id={fw_id} name={name}")
        _api_request(token, "DELETE", f"/v2/firewalls/{fw_id}")

    print("[cleanup] complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
