"""Async schedule fetcher with primary/fallback sources and local disk cache."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from config import KYIV_TZ
from schedule import day_timestamp_for

logger = logging.getLogger(__name__)


def _parse_last_updated(payload: dict[str, Any]) -> datetime:
    raw = payload.get("lastUpdated")
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def _is_valid_payload(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("fact"), dict)
        and isinstance(payload["fact"].get("data"), dict)
        and len(payload["fact"]["data"]) > 0
    )


class ScheduleFetcher:
    """Fetches and caches Zaporizhzhia outage JSON from GitHub sources."""

    def __init__(self, primary_url: str, fallback_url: str, cache_path: Path) -> None:
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.cache_path = cache_path
        self._data: dict[str, Any] | None = self._load_disk_cache()

    @property
    def data(self) -> dict[str, Any] | None:
        return self._data

    def _load_disk_cache(self) -> dict[str, Any] | None:
        if not self.cache_path.is_file():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if _is_valid_payload(payload):
                return payload
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read disk cache %s: %s", self.cache_path, exc)
        return None

    def _save_disk_cache(self, payload: dict[str, Any]) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to save disk cache %s: %s", self.cache_path, exc)

    async def _fetch_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
        if not url:
            return None
        try:
            resp = await client.get(url, timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            payload = resp.json()
            if _is_valid_payload(payload):
                return payload
            logger.warning("Invalid schedule payload from %s", url)
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Failed to fetch schedule from %s: %s", url, exc)
        return None

    async def refresh(self) -> dict[str, Any] | None:
        """Fetch latest schedule from primary and fallback in parallel, returning freshest valid payload."""
        headers = {
            "User-Agent": "zaporizhzhia-svitlo-bot/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        async with httpx.AsyncClient(headers=headers) as client:
            results = await asyncio.gather(
                self._fetch_json(client, self.primary_url),
                self._fetch_json(client, self.fallback_url),
                return_exceptions=True,
            )

        candidates = [r for r in results if isinstance(r, dict)]
        if not candidates:
            return self._data

        best = max(candidates, key=_parse_last_updated)
        if self._data is None or _parse_last_updated(best) >= _parse_last_updated(self._data):
            self._data = best
            self._save_disk_cache(best)
        return self._data
