from __future__ import annotations

import pytest

import requests

from name_finder.scrape_common_surnames import (
    GermanSurnameScraper,
    fetch_html,
)


SAMPLE_HTML = """
<html>
  <body>
    <h2 id="Liste_der_3_häufigsten_Familiennamen_in_Deutschland">
      Liste der 3 häufigsten Familiennamen in Deutschland
    </h2>
    <ol>
      <li><a href="/wiki/M%C3%BCller">Müller</a>, Berufsbezeichnung <sup>[1]</sup></li>
      <li>
        <a href="/wiki/Schneider">Schneider</a> und
        <a href="/wiki/Andere">Other</a> Varianten
      </li>
      <li><a href="/wiki/Fischer">Fischer</a></li>
    </ol>
  </body>
</html>
"""


def test_german_scraper_extracts_expected_surnames() -> None:
    scraper = GermanSurnameScraper()
    scraper.heading_id = "Liste_der_3_häufigsten_Familiennamen_in_Deutschland"
    scraper.source_url = "https://example.org"

    result = scraper.parse(SAMPLE_HTML)

    assert [entry["surname"] for entry in result] == ["Müller", "Schneider", "Fischer"]
    assert [entry["rank"] for entry in result] == [1, 2, 3]
    assert len(result) == 3
    assert all(entry["country"] == "de" for entry in result)


def test_german_scraper_raises_when_count_mismatch() -> None:
    scraper = GermanSurnameScraper()
    scraper.heading_id = "Liste_der_2_häufigsten_Familiennamen_in_Deutschland"
    bad_html = SAMPLE_HTML.replace("3", "2")

    with pytest.raises(RuntimeError):
        scraper.parse(bad_html)


def test_fetch_html_uses_headers_and_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, str] = {}

    class DummyResponse:
        text = "<html></html>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, headers: dict, timeout: int) -> DummyResponse:
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    html = fetch_html("https://example.org")

    assert html == "<html></html>"
    assert calls["timeout"] == 20
    assert "User-Agent" in calls["headers"]
    assert calls["headers"]["User-Agent"].startswith("name-finder-scraper")


def test_fetch_html_raises_runtime_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            raise requests.HTTPError("403")

    def fake_get(*args, **kwargs) -> DummyResponse:
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="Failed to fetch"):
        fetch_html("https://example.org/bad")
