from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from name_finder.domain.models import FirstName, NameCountry, NameGender, NameSource


class ScraperError(RuntimeError):
    """Raised when a scraper operation fails."""


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        attributes = dict(attrs)
        href = attributes.get("href")
        if href is not None:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return

        text = " ".join("".join(self._current_text).split())
        self.anchors.append((self._current_href, text))
        self._current_href = None
        self._current_text = []


@dataclass(slots=True)
class PopularNamesDEScraper:
    """Downloads first names from the German source site lexicon pages."""

    start_url: str = "https://www.beliebte-vornamen.de/lexikon/"
    timeout_seconds: int = 30

    def download_names(self, max_pages: int = 15) -> list[FirstName]:
        visited: set[str] = set()
        queue: deque[str] = deque([self.start_url])
        names: dict[tuple[str, NameGender], FirstName] = {}

        while queue and len(visited) < max_pages:
            page_url = queue.popleft()
            if page_url in visited:
                continue

            html = self._fetch(page_url)
            visited.add(page_url)

            for name in _extract_name_candidates(html, page_url):
                names.setdefault((name.value.casefold(), name.gender), name)

            for link in _extract_lexicon_links(html, page_url):
                if link not in visited:
                    queue.append(link)

        return sorted(names.values(), key=lambda n: (n.value.casefold(), n.gender.value))

    def _fetch(self, url: str) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                if status >= 400:
                    raise ScraperError(f"Could not fetch {url}: HTTP {status}")
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            raise ScraperError(f"Could not fetch {url}: {exc}") from exc


def _extract_anchors(html: str) -> Iterable[tuple[str, str]]:
    parser = _AnchorParser()
    parser.feed(html)
    return parser.anchors


def _extract_lexicon_links(html: str, page_url: str) -> Iterable[str]:
    for href, _ in _extract_anchors(html):
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != "www.beliebte-vornamen.de":
            continue
        if "/lexikon/" not in parsed.path:
            continue
        if absolute.startswith("https://www.beliebte-vornamen.de/lexikon/"):
            yield absolute


def _extract_name_candidates(html: str, page_url: str) -> Iterable[FirstName]:
    page_gender = _infer_gender_from_url(page_url)

    for href, text in _extract_anchors(html):
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc != "www.beliebte-vornamen.de":
            continue
        if "/vornamen/" not in parsed.path:
            continue
        if not _looks_like_first_name(text):
            continue

        gender = _infer_gender_from_url(absolute)
        if gender == NameGender.UNKNOWN:
            gender = page_gender

        yield FirstName(
            value=text,
            source_url=absolute,
            gender=gender,
            country=NameCountry.GERMANY,
            source=NameSource.POPULAR_FIRST_NAMES_DE,
        )


def _infer_gender_from_url(url: str) -> NameGender:
    path = urlparse(url).path.casefold()
    if path.endswith("-frau") or "-frau/" in path:
        return NameGender.FEMALE
    if path.endswith("-mann") or "-mann/" in path:
        return NameGender.MALE
    return NameGender.UNKNOWN


def _looks_like_first_name(value: str) -> bool:
    if len(value) < 2 or len(value) > 30:
        return False
    if any(ch.isdigit() for ch in value):
        return False

    allowed_extra = {"-", " ", "'", "’"}
    return all(ch.isalpha() or ch in allowed_extra for ch in value)
