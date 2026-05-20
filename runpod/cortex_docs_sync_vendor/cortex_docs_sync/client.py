"""HTTP client for the Cortex Documentation Hub FluidTopics JSON API."""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import List, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from cortex_docs_sync.models import CORTEX_BASE_URL, Publication

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; Cortex-Workbench/1.0; +https://github.com/n0081183/simple-rag) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
DEFAULT_RATE_LIMIT_RPS = 1.0
MAX_BACKOFF_SECONDS = 90.0
FAST_MAX_BACKOFF_SECONDS = 30.0

logger = logging.getLogger(__name__)
_thread_local = threading.local()


class RateLimiter:
    """Per-thread spacing: each worker may sustain ``requests_per_second`` independently."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / max(float(requests_per_second), 0.05)
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
            jitter = random.uniform(0.0, 0.1 * self._min_interval)
            self._next_allowed = time.monotonic() + self._min_interval + jitter


class CortexDocsClient:
    """GET client with per-thread rate limits (aggregate ≈ rate × parallel workers)."""

    def __init__(
        self,
        base_url: str = CORTEX_BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        rate_limit_rps: float = DEFAULT_RATE_LIMIT_RPS,
        timeout_seconds: int = 60,
        max_retries: int = 5,
        fast_backoff: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/html;q=0.8, */*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        retries = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._rate_limit_rps = max(float(rate_limit_rps), 0.05)
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self._fast_backoff = fast_backoff
        self._max_backoff = FAST_MAX_BACKOFF_SECONDS if fast_backoff else MAX_BACKOFF_SECONDS

    def _limiter(self) -> RateLimiter:
        if getattr(_thread_local, "cortex_rps", None) != self._rate_limit_rps:
            _thread_local.cortex_rps = self._rate_limit_rps
            _thread_local.cortex_limiter = RateLimiter(self._rate_limit_rps)
        return _thread_local.cortex_limiter

    def _backoff_seconds(self, resp: requests.Response | None, attempt: int) -> float:
        if resp is not None and resp.status_code == 429:
            raw = resp.headers.get("Retry-After") or resp.headers.get("retry-after")
            if raw:
                try:
                    return min(self._max_backoff, max(float(raw), 2.0))
                except ValueError:
                    pass
            base = 5.0 if self._fast_backoff else 10.0
            return min(self._max_backoff, base * (2 ** (attempt - 1)) + random.uniform(0, 1))
        return min(30.0, 1.5 ** (attempt - 1) + random.uniform(0, 0.5))

    def _get(self, path: str, params: Optional[dict] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_exc: Optional[BaseException] = None
        last_resp: requests.Response | None = None

        for attempt in range(1, self.max_retries + 1):
            self._limiter().wait()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                last_resp = resp

                if resp.status_code == 429:
                    backoff = self._backoff_seconds(resp, attempt)
                    logger.warning(
                        "GET %s rate limited 429 (attempt %d/%d) — sleeping %.1fs",
                        path,
                        attempt,
                        self.max_retries,
                        backoff,
                    )
                    if attempt >= self.max_retries:
                        resp.raise_for_status()
                    time.sleep(backoff)
                    continue

                if resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"HTTP {resp.status_code} from {url}", response=resp
                    )

                resp.raise_for_status()
                return resp
            except (requests.RequestException, requests.HTTPError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    backoff = self._backoff_seconds(last_resp, attempt)
                    logger.warning(
                        "GET %s failed (attempt %d/%d): %s — retrying in %.1fs",
                        path,
                        attempt,
                        self.max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "GET %s failed after %d attempts: %s",
                        path,
                        attempt,
                        exc,
                    )

        raise RuntimeError(
            f"GET {path} failed after {self.max_retries} attempts"
        ) from last_exc

    def list_publications(self, limit: int = 10000) -> List[Publication]:
        resp = self._get("/api/khub/maps", params={"limit": limit})
        raw = resp.json()
        return [self._parse_publication(item) for item in raw]

    def get_topics(self, map_id: str) -> List[dict]:
        resp = self._get(f"/api/khub/maps/{quote(map_id)}/topics")
        return resp.json()

    def get_topic_content(self, map_id: str, topic_id: str) -> str:
        resp = self._get(
            f"/api/khub/maps/{quote(map_id)}/topics/{quote(topic_id)}/content"
        )
        return resp.text

    @staticmethod
    def _parse_publication(item: dict) -> Publication:
        meta_lookup: dict[str, list[str]] = {}
        for meta in item.get("metadata", []):
            key = meta.get("key")
            values = meta.get("values") or []
            if key:
                meta_lookup[key] = values

        def first(key: str) -> Optional[str]:
            values = meta_lookup.get(key)
            return values[0] if values else None

        version: Optional[str] = None
        sub = first("subtitle")
        if sub and "version" in sub.lower():
            version = sub.split(":", 1)[-1].strip()
        elif first("xinfo:version_major"):
            major = first("xinfo:version_major")
            minor = first("xinfo:version_minor")
            version = f"{major}.{minor}" if minor else major

        word_count: Optional[int] = None
        wc_raw = first("ft:wordCount")
        if wc_raw:
            try:
                word_count = int(wc_raw)
            except ValueError:
                pass

        return Publication(
            map_id=item["id"],
            title=item.get("title", ""),
            products=meta_lookup.get("Product", []),
            category=first("Category"),
            version=version,
            last_edition=first("ft:lastEdition"),
            last_tech_change=first("ft:lastTechChange"),
            word_count=word_count,
            pretty_url=first("ft:prettyUrl") or "",
        )
