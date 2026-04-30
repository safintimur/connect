from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class OperationResult:
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    incident_id: str
    created_at: str
    operation: str
    stage: str
    summary: str
    context: dict[str, Any]
    status: str = "new"
    workflow_url: str = ""
    run_id: int | None = None
    pr_number: int | None = None

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
