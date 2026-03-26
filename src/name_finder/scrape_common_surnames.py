#!/usr/bin/env python3
"""Scrape common surnames from Wikipedia."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Protocol

import requests
from bs4 import BeautifulSoup, Tag

GERMANY_URL = "https://de.wikipedia.org/wiki/Liste_der_h%C3%A4ufigsten_Familiennamen_in_Deutschland"
GERMANY_HEADING_ID = "Liste_der_120_häufigsten_Familiennamen_in_Deutschland"
OUTPUT_PATH = Path("data") / "common_surnames_de.json"
DECLARED_COUNT_PATTERN = re.compile(r"(\d+)")
DEFAULT_HEADERS = {
    "User-Agent": "name-finder-scraper/1.0 (+https://github.com/ffloegel/codex-find-first-name)",
    "Accept-Language": "de,en;q=0.9",
}


def fetch_html(url: str) -> str:
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch '{url}': {exc}") from exc
    return response.text


def extract_declared_count_from_heading(heading: Tag) -> int | None:
    text = heading.get_text(" ", strip=True)
    match = DECLARED_COUNT_PATTERN.search(text)
    return int(match.group(1)) if match else None


class SurnameScraperStrategy(Protocol):
    country: str
    source_url: str

    def parse(self, html: str) -> list[dict]:
        ...


class GermanSurnameScraper:
    country = "de"
    source_url = GERMANY_URL
    heading_id = GERMANY_HEADING_ID

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find("h2", id=self.heading_id)
        if heading is None:
            raise RuntimeError(f"Could not locate heading with id '{self.heading_id}'")
        declared_count = extract_declared_count_from_heading(heading)
        list_tag = heading.find_next(["ol", "ul"])
        if list_tag is None:
            raise RuntimeError("Could not locate surname list following the heading")

        surnames = _collect_surnames(list_tag, self.country, self.source_url)
        if declared_count is not None and len(surnames) != declared_count:
            raise RuntimeError(
                f"Declared {declared_count} surnames but extracted {len(surnames)}."
            )
        return surnames


COUNTRY_STRATEGIES: dict[str, SurnameScraperStrategy] = {
    "de": GermanSurnameScraper(),
}


def _collect_surnames(list_tag: Tag, country: str, source_url: str) -> list[dict]:
    items = list_tag.find_all("li", recursive=False)
    if not items:
        items = list_tag.find_all("li")
    records: list[dict] = []
    for index, li in enumerate(items, start=1):
        surname = _extract_first_anchor_text(li)
        if not surname:
            continue
        records.append(
            {
                "surname": surname,
                "country": country,
                "source": source_url,
                "rank": index,
            }
        )
    return records


def _extract_first_anchor_text(node: Tag) -> str | None:
    anchor = node.find("a")
    if not anchor:
        return None
    text = anchor.get_text(strip=True)
    return text or None


def scrape_common_surnames(country: str, output_path: Path | None = None) -> list[dict]:
    strategy = COUNTRY_STRATEGIES.get(country)
    if strategy is None:
        supported = ", ".join(sorted(COUNTRY_STRATEGIES))
        raise ValueError(f"Unsupported country '{country}'. Supported countries: {supported}")
    html = fetch_html(strategy.source_url)
    surnames = strategy.parse(html)

    target_path = output_path or OUTPUT_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(surnames, ensure_ascii=False, indent=2), encoding="utf-8")
    return surnames


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape lists of common surnames")
    parser.add_argument("--country", required=True, help="Country code to scrape (only 'de' supported)")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: data/common_surnames_de.json)",
    )
    args = parser.parse_args()

    surnames = scrape_common_surnames(args.country.lower(), args.output)
    print(f"Scraped {len(surnames)} surnames for country '{args.country.lower()}'.")


if __name__ == "__main__":
    main()
