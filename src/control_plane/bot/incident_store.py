from __future__ import annotations

import json
import uuid
from pathlib import Path

from .models import Incident


class IncidentStore:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, incident_id: str) -> Path:
        return self.base / f"{incident_id}.json"

    def create(self, operation: str, stage: str, summary: str, context: dict) -> Incident:
        incident_id = str(uuid.uuid4())[:8]
        incident = Incident(
            incident_id=incident_id,
            created_at=Incident.now_iso(),
            operation=operation,
            stage=stage,
            summary=summary,
            context=context,
        )
        self.save(incident)
        return incident

    def save(self, incident: Incident) -> None:
        self._path(incident.incident_id).write_text(
            json.dumps(incident.__dict__, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def get(self, incident_id: str) -> Incident | None:
        path = self._path(incident_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Incident(**data)
