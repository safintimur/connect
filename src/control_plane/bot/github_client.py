from __future__ import annotations

import json
from urllib import request


class GitHubClient:
    def __init__(self, token: str, repository: str) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required for bot workflow actions")
        if not repository:
            raise ValueError("GITHUB_REPOSITORY is required (owner/repo)")
        self.token = token
        self.repository = repository
        self.base = "https://api.github.com"

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)

    def dispatch_workflow(self, workflow_file: str, ref: str, inputs: dict | None = None) -> None:
        self._call(
            "POST",
            f"/repos/{self.repository}/actions/workflows/{workflow_file}/dispatches",
            {"ref": ref, "inputs": inputs or {}},
        )

    def list_runs(self, workflow_file: str, branch: str = "main", per_page: int = 10) -> list[dict]:
        result = self._call(
            "GET",
            f"/repos/{self.repository}/actions/workflows/{workflow_file}/runs?branch={branch}&per_page={per_page}",
        )
        return result.get("workflow_runs", [])

    def rerun_failed_jobs(self, run_id: int) -> None:
        self._call("POST", f"/repos/{self.repository}/actions/runs/{run_id}/rerun-failed-jobs")

    def rerun_run(self, run_id: int) -> None:
        self._call("POST", f"/repos/{self.repository}/actions/runs/{run_id}/rerun")

    def merge_pr(self, pr_number: int, method: str = "squash") -> dict:
        return self._call(
            "PUT",
            f"/repos/{self.repository}/pulls/{pr_number}/merge",
            {"merge_method": method},
        )

    def run_url(self, run_id: int) -> str:
        return f"https://github.com/{self.repository}/actions/runs/{run_id}"

    def get_run(self, run_id: int) -> dict:
        return self._call("GET", f"/repos/{self.repository}/actions/runs/{run_id}")

    def get_run_jobs(self, run_id: int) -> list[dict]:
        data = self._call("GET", f"/repos/{self.repository}/actions/runs/{run_id}/jobs?per_page=50")
        return data.get("jobs", [])

    def job_url(self, run_id: int, job_id: int) -> str:
        return f"https://github.com/{self.repository}/actions/runs/{run_id}/job/{job_id}"
