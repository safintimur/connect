from __future__ import annotations

from dataclasses import dataclass

from ..config import settings

try:
    from pydo import Client
except Exception:  # pragma: no cover - import fallback for environments without dependency
    Client = None  # type: ignore[assignment]


@dataclass
class DropletSpec:
    name: str
    region: str | None = None
    size: str | None = None
    image: str | None = None
    tags: list[str] | None = None


class DOProvider:
    def __init__(self, token: str | None = None) -> None:
        api_token = token or settings.do_token
        if not api_token:
            raise ValueError("DigitalOcean token is empty. Set DIGITALOCEAN_TOKEN.")
        if Client is None:
            raise RuntimeError("pydo is not installed in current environment")
        self.client = Client(token=api_token)

    def create_worker_droplet(self, spec: DropletSpec) -> dict:
        req = {
            "name": spec.name,
            "region": spec.region or settings.do_default_region,
            "size": spec.size or settings.do_default_size,
            "image": spec.image or settings.do_default_image,
            "tags": spec.tags or ["connect", "worker", "uk"],
            "ipv6": False,
            "monitoring": True,
        }
        return self.client.droplets.create(body=req)

    def get_droplet(self, droplet_id: int) -> dict:
        return self.client.droplets.get(droplet_id=droplet_id)

    def delete_droplet(self, droplet_id: int) -> dict:
        return self.client.droplets.destroy(droplet_id=droplet_id)
