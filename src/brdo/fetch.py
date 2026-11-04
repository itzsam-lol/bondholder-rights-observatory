"""Policy-aware retrieval of source documents into a content-addressed cache.

The fetcher only contacts hosts that belong to a registered source whose
retrieval policy is ``allowed``, obeys robots.txt and crawl delays, identifies
itself, and never attempts to get past authentication or access controls.
Retrieved files stay in a local cache; they are never written into the
repository.
"""

import hashlib
import http.client
import json
import os
import time
import urllib.error
import urllib.request
import urllib.robotparser
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

from brdo.models import Source
from brdo.vocab import RetrievalPolicy

USER_AGENT = "bondholder-rights-observatory/0.1 (+https://github.com/itzsam-lol/bondholder-rights-observatory)"
DEFAULT_MIN_INTERVAL_SECONDS = 5.0
DEFAULT_TIMEOUT_SECONDS = 90.0


def default_cache_dir() -> Path:
    return Path(os.environ.get("BRDO_CACHE", ".cache/brdo"))


class RetrievalRefused(Exception):
    """The project's source policy or the site's robots.txt does not permit this retrieval."""


class RetrievalFailed(Exception):
    """The server did not return the document."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes
    final_url: str


HttpGet = Callable[[str, dict[str, str]], HttpResponse]


def urllib_get(url: str, headers: dict[str, str]) -> HttpResponse:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            return HttpResponse(
                status=response.status,
                headers={key.lower(): value for key, value in response.headers.items()},
                body=response.read(),
                final_url=response.geturl(),
            )
    except urllib.error.HTTPError as error:
        return HttpResponse(
            status=error.code,
            headers={key.lower(): value for key, value in error.headers.items()},
            body=b"",
            final_url=url,
        )
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        raise RetrievalFailed(f"{url}: {error}") from error


@dataclass(frozen=True)
class Retrieved:
    url: str
    final_url: str
    sha256: str
    size_bytes: int
    media_type: str | None
    last_modified: datetime | None
    retrieved_at: datetime
    path: Path


class Cache:
    """Files keyed by their SHA-256, with a JSON sidecar describing each retrieval."""

    def __init__(self, root: Path):
        self.root = root

    def path_for(self, sha256: str) -> Path:
        return self.root / "objects" / sha256[:2] / sha256

    def get(self, sha256: str) -> Path | None:
        path = self.path_for(sha256)
        return path if path.exists() else None

    def store(self, body: bytes, metadata: dict[str, object]) -> tuple[str, Path]:
        sha256 = hashlib.sha256(body).hexdigest()
        path = self.path_for(sha256)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temporary = path.with_suffix(".partial")
            temporary.write_bytes(body)
            temporary.replace(path)
        sidecar = path.with_suffix(".json")
        sidecar.write_text(json.dumps(metadata, indent=2, sort_keys=True, default=str), encoding="utf-8")
        return sha256, path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_for_url(url: str, sources: Iterable[Source]) -> Source | None:
    host = (urlsplit(url).hostname or "").lower()
    for source in sources:
        for domain in source.domains:
            domain = domain.lower()
            if host == domain or host.endswith("." + domain):
                return source
    return None


class Fetcher:
    def __init__(
        self,
        sources: Iterable[Source],
        cache: Cache,
        *,
        http_get: HttpGet = urllib_get,
        user_agent: str = USER_AGENT,
        min_interval: float = DEFAULT_MIN_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.sources = list(sources)
        self.cache = cache
        self.http_get = http_get
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.clock = clock
        self.sleep = sleep
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._robots_unread: dict[str, str] = {}
        self._last_request: dict[str, float] = {}

    def check_allowed(self, url: str) -> Source:
        """Return the source for ``url``, or raise ``RetrievalRefused``, or ``RetrievalFailed`` if robots.txt is unread.

        A robots file that cannot be read stops retrieval just as a refusal does, but it is reported as a failure to
        read it, so that a search log records an access error rather than a restriction the site never stated.
        """
        source = source_for_url(url, self.sources)
        if source is None:
            raise RetrievalRefused(f"{url}: host is not a registered source; add it to sources.yaml first")
        if source.retrieval is not RetrievalPolicy.ALLOWED:
            raise RetrievalRefused(f"{url}: retrieval policy for {source.id} is {source.retrieval}")
        robots = self._robots_for(url)
        unread = self._robots_unread.get(urlsplit(url).hostname or "")
        if unread is not None:
            raise RetrievalFailed(f"{url}: robots.txt could not be read ({unread}), so nothing was fetched")
        if robots is not None and not robots.can_fetch(self.user_agent, url):
            raise RetrievalRefused(f"{url}: disallowed by robots.txt")
        return source

    def fetch(self, url: str) -> Retrieved:
        self.check_allowed(url)
        response = self._get(url)
        if response.status != 200:
            raise RetrievalFailed(f"{url}: HTTP {response.status}")
        if _expects_pdf(url) and not response.body.startswith(b"%PDF"):
            raise RetrievalFailed(f"{url}: the server answered with something other than a PDF, such as an error page")
        if response.final_url != url:
            self.check_allowed(response.final_url)
        retrieved_at = datetime.now(UTC).replace(microsecond=0)
        last_modified = _parse_http_date(response.headers.get("last-modified"))
        media_type = (response.headers.get("content-type") or "").split(";")[0].strip() or None
        sha256, path = self.cache.store(
            response.body,
            {
                "url": url,
                "final_url": response.final_url,
                "retrieved_at": retrieved_at.isoformat(),
                "media_type": media_type,
                "last_modified": last_modified.isoformat() if last_modified else None,
                "size_bytes": len(response.body),
            },
        )
        return Retrieved(
            url=url,
            final_url=response.final_url,
            sha256=sha256,
            size_bytes=len(response.body),
            media_type=media_type,
            last_modified=last_modified,
            retrieved_at=retrieved_at,
            path=path,
        )

    def _get(self, url: str) -> HttpResponse:
        host = urlsplit(url).hostname or ""
        delay = self.min_interval
        robots = self._robots.get(host)
        if robots is not None:
            crawl_delay = robots.crawl_delay(self.user_agent)
            if crawl_delay:
                delay = max(delay, float(crawl_delay))
        last = self._last_request.get(host)
        if last is not None:
            wait = delay - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        try:
            return self.http_get(url, {"User-Agent": self.user_agent, "Accept": "*/*"})
        finally:
            self._last_request[host] = self.clock()

    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser | None:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if host in self._robots:
            return self._robots[host]
        parser = urllib.robotparser.RobotFileParser()
        try:
            response = self._get(f"{parts.scheme}://{parts.netloc}/robots.txt")
        except RetrievalFailed as error:
            parser.disallow_all = True
            self._robots_unread[host] = str(error).removeprefix(f"{parts.scheme}://{parts.netloc}/robots.txt: ")
        else:
            if response.status == 200 and _looks_like_robots(response):
                parser.parse(response.body.decode("utf-8", errors="replace").splitlines())
            elif response.status >= 500:
                parser.disallow_all = True
                self._robots_unread[host] = f"HTTP {response.status}"
            else:
                parser.allow_all = True
        self._robots[host] = parser
        return parser


def _expects_pdf(url: str) -> bool:
    return urlsplit(url).path.lower().endswith(".pdf")


def _looks_like_robots(response: HttpResponse) -> bool:
    """Some servers answer /robots.txt with an HTML page; treat that as no robots file."""
    content_type = response.headers.get("content-type", "")
    head = response.body[:512].lstrip().lower()
    return "html" not in content_type and not head.startswith((b"<!doctype", b"<html"))


def _parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(UTC)
    except (TypeError, ValueError):
        return None
