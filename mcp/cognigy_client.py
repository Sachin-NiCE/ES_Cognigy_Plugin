"""Thin HTTP client for the Cognigy.AI REST API.

Endpoint prefixes are split, matching the platform's own routing:
- Older resources (snapshots) live under /v2.0/...
- Newer resources (packages, project settings, tasks) live under /new/v2.0/...

Both prefixes hit the same API and share auth (X-API-Key) and error shape
(RFC 7807 Problem Details).
"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from cognigy_config import get_api_key, get_base_url

TERMINAL_TASK_STATUSES = {"done", "error", "cancelled"}


class CognigyAPIError(RuntimeError):
    def __init__(self, status_code: int, problem: dict[str, Any]):
        self.status_code = status_code
        self.problem = problem
        detail = problem.get("detail") or problem.get("title") or "Cognigy API error"
        super().__init__(f"[{status_code}] {detail}")


class CognigyTaskError(RuntimeError):
    def __init__(self, task: dict[str, Any]):
        self.task = task
        reason = task.get("failReason") or task.get("status")
        super().__init__(f"Cognigy task failed: {reason}")


class CognigyClient:
    def __init__(self) -> None:
        base_url = get_base_url()
        api_key = get_api_key()
        if not base_url or not api_key:
            raise RuntimeError(
                "Cognigy is not configured. Ask the user to run /cognigy-setup "
                "to set the API base URL and API key."
            )
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": api_key},
            timeout=60.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CognigyClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _handle(self, resp: httpx.Response) -> Any:
        if resp.status_code >= 400:
            try:
                problem = resp.json()
            except ValueError:
                problem = {"title": resp.text or resp.reason_phrase}
            raise CognigyAPIError(resp.status_code, problem)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        return self._handle(resp)

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json: Optional[dict[str, Any]] = None, **kwargs: Any) -> Any:
        return self.request("POST", path, json=json, **kwargs)

    def patch(self, path: str, json: Optional[dict[str, Any]] = None) -> Any:
        return self.request("PATCH", path, json=json)

    def delete(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return self.request("DELETE", path, params=params)

    def get_absolute_bytes(self, url: str) -> bytes:
        """GET a fully-qualified URL (e.g. a pre-signed download link) that is
        not necessarily under base_url, reusing this client's connection pool.
        """
        resp = self._client.get(url)
        resp.raise_for_status()
        return resp.content

    def get_task(self, task_id: str, project_id: str) -> dict[str, Any]:
        return self.get(f"/new/v2.0/tasks/{task_id}", params={"projectId": project_id})

    def wait_for_task(
        self,
        task: dict[str, Any],
        project_id: str,
        timeout_s: float = 600.0,
        poll_interval_s: float = 3.0,
    ) -> dict[str, Any]:
        """Poll a task until it reaches a terminal status, or the timeout elapses.

        Raises CognigyTaskError if the task ends in "error". Returns the last-seen
        task dict either on success, cancellation, or timeout (callers should check
        `status` when this returns without raising).
        """
        task_id = task.get("_id") or task.get("id")
        if not task_id:
            return task

        deadline = time.monotonic() + timeout_s
        current = task
        while current.get("status") not in TERMINAL_TASK_STATUSES:
            if time.monotonic() >= deadline:
                current["_timedOut"] = True
                return current
            time.sleep(poll_interval_s)
            current = self.get_task(task_id, project_id)

        if current.get("status") == "error":
            raise CognigyTaskError(current)
        return current
