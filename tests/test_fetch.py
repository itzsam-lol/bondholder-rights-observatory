"""The fetcher must refuse what the source policy or robots.txt forbids, without being able to be talked around."""

import http.client
import urllib.request
from datetime import UTC, datetime

import pytest

from brdo.fetch import (
    Cache,
    Fetcher,
    HttpResponse,
    RetrievalFailed,
    RetrievalRefused,
    file_sha256,
    source_for_url,
    urllib_get,
)
from brdo.vocab import RedistributionPolicy, RetrievalPolicy
from tests.conftest import make_source

PDF = b"%PDF-1.7 body"


class FakeWeb:
    """Serves canned responses and records every request, so tests can assert what was never asked for."""

    def __init__(self, pages: dict[str, HttpResponse] | None = None):
        self.pages = pages or {}
        self.requests: list[tuple[str, dict]] = []

    def __call__(self, url: str, headers: dict[str, str]) -> HttpResponse:
        self.requests.append((url, headers))
        return self.pages.get(url, HttpResponse(404, {}, b"", url))


def ok(url: str, body: bytes = PDF, content_type: str = "application/pdf", **headers) -> HttpResponse:
    return HttpResponse(200, {"content-type": content_type, **headers}, body, url)


URL = "https://trustee-a.example/report.pdf"
ROBOTS = "https://trustee-a.example/robots.txt"


def fetcher(tmp_path, web, *sources, **options) -> Fetcher:
    return Fetcher(sources or [make_source()], Cache(tmp_path), http_get=web, sleep=lambda _: None, **options)


def test_retrieves_hashes_and_caches_a_permitted_document(tmp_path):
    web = FakeWeb({URL: ok(URL, **{"last-modified": "Sun, 13 Sep 2026 16:48:23 GMT"})})
    retrieved = fetcher(tmp_path, web).fetch(URL)
    assert retrieved.size_bytes == len(PDF)
    assert retrieved.path.read_bytes() == PDF
    assert file_sha256(retrieved.path) == retrieved.sha256
    assert retrieved.last_modified == datetime(2026, 9, 13, 16, 48, 23, tzinfo=UTC)
    assert retrieved.media_type == "application/pdf"


def test_identifies_itself_honestly(tmp_path):
    web = FakeWeb({URL: ok(URL)})
    fetcher(tmp_path, web).fetch(URL)
    user_agents = {headers["User-Agent"] for _, headers in web.requests}
    assert len(user_agents) == 1
    agent = user_agents.pop()
    assert agent.startswith("bondholder-rights-observatory/")
    assert "Mozilla" not in agent


def test_refuses_hosts_that_are_not_registered_sources_without_contacting_them(tmp_path):
    web = FakeWeb()
    with pytest.raises(RetrievalRefused, match="not a registered source"):
        fetcher(tmp_path, web).fetch("https://unknown.example/a.pdf")
    assert web.requests == []


@pytest.mark.parametrize("policy", [RetrievalPolicy.MANUAL_ONLY, RetrievalPolicy.EXCLUDED])
def test_refuses_sources_the_policy_closes_without_contacting_them(tmp_path, policy):
    web = FakeWeb()
    with pytest.raises(RetrievalRefused, match="retrieval policy"):
        fetcher(tmp_path, web, make_source(retrieval=policy)).fetch(URL)
    assert web.requests == []


def test_subdomains_inherit_their_source_policy(tmp_path):
    closed = make_source("exchange", domains=["exchange.example"], retrieval=RetrievalPolicy.EXCLUDED)
    assert source_for_url("https://archives.exchange.example/a.pdf", [closed]) is closed
    assert source_for_url("https://notexchange.example/a.pdf", [closed]) is None


def test_obeys_robots_disallow(tmp_path):
    robots = ok(ROBOTS, b"User-agent: *\nDisallow: /report.pdf\n", "text/plain")
    web = FakeWeb({ROBOTS: robots, URL: ok(URL)})
    with pytest.raises(RetrievalRefused, match="robots.txt"):
        fetcher(tmp_path, web).fetch(URL)
    assert URL not in [url for url, _ in web.requests]


def test_treats_an_unreachable_robots_file_as_disallowing_everything(tmp_path):
    web = FakeWeb({ROBOTS: HttpResponse(503, {}, b"", ROBOTS), URL: ok(URL)})
    with pytest.raises(RetrievalFailed, match="robots.txt could not be read"):
        fetcher(tmp_path, web).fetch(URL)
    assert URL not in [url for url, _ in web.requests]


def test_a_robots_file_that_cannot_be_reached_is_reported_as_unread_not_as_a_refusal(tmp_path):
    def unreachable(url: str, headers: dict[str, str]) -> HttpResponse:
        raise RetrievalFailed(f"{url}: <urlopen error Tunnel connection failed: 403 Forbidden>")

    with pytest.raises(RetrievalFailed, match=r"robots.txt could not be read \(<urlopen error Tunnel"):
        fetcher(tmp_path, unreachable).check_allowed(URL)


def test_a_missing_robots_file_allows_retrieval(tmp_path):
    web = FakeWeb({URL: ok(URL)})
    assert fetcher(tmp_path, web).fetch(URL).size_bytes == len(PDF)


def test_an_html_page_at_the_robots_address_is_not_a_robots_file(tmp_path):
    page = ok(ROBOTS, b"<!doctype html><html>Disallow: /</html>", "text/html")
    web = FakeWeb({ROBOTS: page, URL: ok(URL)})
    assert fetcher(tmp_path, web).fetch(URL).size_bytes == len(PDF)


def test_an_error_page_served_with_status_200_is_not_the_document(tmp_path):
    """BSE's edge filter answers a refused client with an HTML error page and HTTP 200."""
    page = ok(URL, b"<html>This page can't be displayed.</html>", "text/html")
    with pytest.raises(RetrievalFailed, match="other than a PDF"):
        fetcher(tmp_path, FakeWeb({URL: page})).fetch(URL)


def test_http_errors_are_reported(tmp_path):
    web = FakeWeb({URL: HttpResponse(406, {}, b"", URL)})
    with pytest.raises(RetrievalFailed, match="HTTP 406"):
        fetcher(tmp_path, web).fetch(URL)


def test_a_redirect_into_a_closed_source_is_refused_and_not_stored(tmp_path):
    closed = make_source("closed", domains=["closed.example"], retrieval=RetrievalPolicy.EXCLUDED)
    moved = HttpResponse(200, {"content-type": "application/pdf"}, PDF, "https://closed.example/report.pdf")
    with pytest.raises(RetrievalRefused):
        fetcher(tmp_path, FakeWeb({URL: moved}), make_source(), closed).fetch(URL)
    assert not (tmp_path / "objects").exists()


def _timed_fetches(tmp_path, robots: HttpResponse | None) -> list[float]:
    second = "https://trustee-a.example/second.pdf"
    pages = {URL: ok(URL), second: ok(second)}
    if robots is not None:
        pages[ROBOTS] = robots
    now = {"t": 0.0}
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        now["t"] += seconds

    instance = Fetcher(
        [make_source()], Cache(tmp_path), http_get=FakeWeb(pages), sleep=sleep, clock=lambda: now["t"], min_interval=5.0
    )
    instance.fetch(URL)
    instance.fetch(second)
    return waits


def test_keeps_a_minimum_interval_between_requests_to_a_host(tmp_path):
    assert _timed_fetches(tmp_path, None) == [5.0, 5.0]


def test_a_longer_crawl_delay_in_robots_wins(tmp_path):
    robots = ok(ROBOTS, b"User-agent: *\nCrawl-delay: 10\n", "text/plain")
    assert _timed_fetches(tmp_path, robots) == [10.0, 10.0]


def test_the_same_content_is_stored_once(tmp_path):
    cache = Cache(tmp_path)
    first, path = cache.store(PDF, {"url": "a"})
    second, _ = cache.store(PDF, {"url": "b"})
    assert first == second
    assert cache.get(first) == path
    assert cache.get("0" * 64) is None


def test_the_nse_policy_cannot_be_retrieved_or_linked():
    source = make_source(
        "nse",
        domains=["nseindia.com"],
        retrieval=RetrievalPolicy.EXCLUDED,
        redistribution=RedistributionPolicy.NO_LINKS,
    )
    assert source_for_url("https://nsearchives.nseindia.com/x.pdf", [source]) is source


def test_a_download_cut_off_midway_is_reported_as_a_failure(monkeypatch):
    class Truncated:
        status = 200
        headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            raise http.client.IncompleteRead(b"%PDF-1.7", 100)

        def geturl(self):
            return "https://example.org/a.pdf"

    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: Truncated())
    with pytest.raises(RetrievalFailed, match="IncompleteRead"):
        urllib_get("https://example.org/a.pdf", {})
