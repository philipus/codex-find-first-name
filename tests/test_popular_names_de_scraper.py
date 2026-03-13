from urllib.error import HTTPError

from name_finder.data.scrapers.popular_names_de import (
    PopularNamesDEScraper,
    ScraperError,
    _extract_lexicon_links,
    _extract_name_candidates,
    _infer_gender_from_url,
)
from name_finder.domain.models import NameCountry, NameGender, NameSource


INDEX_HTML = """
<html><body>
  <a href="/lexikon/a-frau">A girls</a>
  <a href="/lexikon/a-mann">A boys</a>
  <a href="/other/">Other</a>
</body></html>
"""


class StubResponse:
    def __init__(self, text: str, status: int = 200):
        self._text = text
        self.status = status

    def read(self) -> bytes:
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_extract_lexicon_links_filters_non_lexicon_links() -> None:
    links = list(_extract_lexicon_links(INDEX_HTML, "https://www.beliebte-vornamen.de/lexikon/"))
    assert links == [
        "https://www.beliebte-vornamen.de/lexikon/a-frau",
        "https://www.beliebte-vornamen.de/lexikon/a-mann",
    ]


def test_extract_name_candidates_inherits_gender_from_page_url_and_sets_categories() -> None:
    html = '<a href="/vornamen/anna.htm">Anna</a><a href="/vornamen/lia.htm">Lia</a>'
    candidates = list(_extract_name_candidates(html, "https://www.beliebte-vornamen.de/lexikon/a-frau"))

    assert [item.value for item in candidates] == ["Anna", "Lia"]
    assert all(item.gender == NameGender.FEMALE for item in candidates)
    assert all(item.country == NameCountry.GERMANY for item in candidates)
    assert all(item.source == NameSource.POPULAR_FIRST_NAMES_DE for item in candidates)


def test_infer_gender_from_url() -> None:
    assert _infer_gender_from_url("https://www.beliebte-vornamen.de/lexikon/a-frau") == NameGender.FEMALE
    assert _infer_gender_from_url("https://www.beliebte-vornamen.de/lexikon/a-mann") == NameGender.MALE
    assert _infer_gender_from_url("https://www.beliebte-vornamen.de/vornamen/anna.htm") == NameGender.UNKNOWN


def test_scraper_raises_error_on_http_failure(monkeypatch) -> None:
    def fake_urlopen(*_args, **_kwargs):
        raise HTTPError(url="https://example.com", code=403, msg="Forbidden", hdrs=None, fp=None)

    monkeypatch.setattr("name_finder.data.scrapers.popular_names_de.urlopen", fake_urlopen)

    scraper = PopularNamesDEScraper()

    try:
        scraper.download_names()
    except ScraperError as error:
        assert "403" in str(error)
    else:
        raise AssertionError("Expected ScraperError")


def test_scraper_collects_unique_names_per_gender(monkeypatch) -> None:
    pages = {
        "https://www.beliebte-vornamen.de/lexikon/": StubResponse(INDEX_HTML),
        "https://www.beliebte-vornamen.de/lexikon/a-frau": StubResponse(
            '<a href="/vornamen/anna.htm">Anna</a><a href="/vornamen/alex.htm">Alex</a>'
        ),
        "https://www.beliebte-vornamen.de/lexikon/a-mann": StubResponse(
            '<a href="/vornamen/ben.htm">Ben</a><a href="/vornamen/alex.htm">Alex</a>'
        ),
    }

    def fake_urlopen(request, **_kwargs):
        return pages[request.full_url]

    monkeypatch.setattr("name_finder.data.scrapers.popular_names_de.urlopen", fake_urlopen)

    scraper = PopularNamesDEScraper()
    result = scraper.download_names(max_pages=5)

    assert [(item.value, item.gender) for item in result] == [
        ("Alex", NameGender.FEMALE),
        ("Alex", NameGender.MALE),
        ("Anna", NameGender.FEMALE),
        ("Ben", NameGender.MALE),
    ]
