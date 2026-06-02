from __future__ import annotations

import logging
import time
from typing import Any

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_SLEEP_TIME = 5
DEFAULT_MAX_RETRIES = 20

log = logging.getLogger("personal_tracker.notion.client")


class NotionAPIError(RuntimeError):
    pass


class DatabaseClient:
    def __init__(
        self,
        database_id: str,
        token: str,
        *,
        sleep_seconds: int = DEFAULT_SLEEP_TIME,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.database_id = database_id
        self.token = token
        self.sleep_seconds = sleep_seconds
        self.max_retries = max_retries
        self._http = http_client or httpx.Client(
            base_url=NOTION_API_BASE,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> DatabaseClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._http.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                if attempt >= self.max_retries:
                    raise NotionAPIError(f"Network error after {attempt} attempts: {exc}") from exc
                log.warning("Network error (%s), retrying in %ss", exc, self.sleep_seconds)
                time.sleep(self.sleep_seconds)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise NotionAPIError(
                        f"{method} {path} failed with {response.status_code} after "
                        f"{attempt} attempts: {response.text}"
                    )
                log.warning(
                    "Notion %s %s -> %s, retrying in %ss (attempt %s/%s)",
                    method,
                    path,
                    response.status_code,
                    self.sleep_seconds,
                    attempt,
                    self.max_retries,
                )
                time.sleep(self.sleep_seconds)
                continue

            if response.status_code >= 400:
                raise NotionAPIError(
                    f"{method} {path} -> {response.status_code}: {response.text}"
                )
            return response

        raise NotionAPIError(f"{method} {path} exhausted retries")

    def retrieve_pages(self, *, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        payload: dict[str, Any] = {}
        if filter is not None:
            payload["filter"] = filter

        cursor: str | None = None
        while True:
            body = dict(payload)
            if cursor:
                body["start_cursor"] = cursor

            response = self._request(
                "POST",
                f"/databases/{self.database_id}/query",
                json=body,
            )
            data = response.json()
            for page in data.get("results", []):
                props = page.get("properties") or {}
                page["properties"] = {
                    name: prop
                    for name, prop in props.items()
                    if (prop or {}).get("type") != "formula"
                }
                results.append(page)

            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break

        return results

    def retrieve_page(self, page_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/pages/{page_id}")
        page = response.json()
        props = page.get("properties") or {}
        page["properties"] = {
            name: prop
            for name, prop in props.items()
            if (prop or {}).get("type") != "formula"
        }
        return page

    def create_page(self, properties: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/pages",
            json={
                "parent": {"database_id": self.database_id},
                "properties": properties,
            },
        )
        return response.json()

    def update_page(self, page_id: str, properties: dict[str, Any]) -> bool:
        response = self._request(
            "PATCH",
            f"/pages/{page_id}",
            json={"properties": properties},
        )
        return bool(response.json())

    def archive_page(self, page_id: str) -> dict[str, Any]:
        response = self._request(
            "PATCH",
            f"/pages/{page_id}",
            json={"archived": True},
        )
        return response.json()

    def add_comment(self, page_id: str, content: str) -> bool:
        response = self._request(
            "POST",
            "/comments",
            json={
                "parent": {"page_id": page_id},
                "rich_text": [{"text": {"content": content}}],
            },
        )
        return response.status_code == 200
