#!/usr/bin/env python3
"""Scrape beliebte-vornamen.de alphabetical name lists."""

from __future__ import annotations

import json
from pathlib import Path
from string import ascii_lowercase
from typing import Iterable, Iterator, List

import requests
from bs4 import BeautifulSoup, Tag

OUTPUT_PATH = Path("data") / "all_names.json"


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def extract_names(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if article is None:
        article = soup.find("main") or soup
    content = article.find(class_="entry-content") if isinstance(article, Tag) else None
    if content is None:
        content = article

    target_list = _find_name_list(content)
    if target_list is not None:
        if target_list.name == "dl":
            raw_entries = (dt.get_text(" ", strip=True) for dt in target_list.find_all("dt"))
        else:
            raw_entries = (li.get_text(" ", strip=True) for li in target_list.find_all("li"))
    else:
        raw_entries = _iter_link_names(content)

    names: List[str] = []
    seen = set()
    for text in raw_entries:
        if not text:
            continue
        name = _normalize_name(text)
        if not name or not _looks_like_name(name) or name in seen:
            continue
        seen.add(name)
        names.append(name)

    if not names:
        raise RuntimeError("Could not locate the primary name list on the page")
    return names


def _find_name_list(content: Tag | None) -> Tag | None:
    if content is None:
        return None
    candidate = content.find(["ul", "ol", "dl"])
    if candidate:
        return candidate
    # Some templates wrap the names inside helper containers (e.g. sections or divs).
    for wrapper in content.find_all(True, recursive=False):
        if not isinstance(wrapper, Tag):
            continue
        nested = wrapper.find(["ul", "ol", "dl"])
        if nested:
            return nested
    return None


def _iter_link_names(content: Tag | None) -> Iterable[str]:
    if content is None:
        return []

    def generator() -> Iterable[str]:
        extracted = 0
        for node in content.descendants:
            if isinstance(node, Tag):
                if node.name in {"h2", "h3"} and extracted:
                    break
                if node.name == "a":
                    text = node.get_text(strip=True)
                    if text:
                        extracted += 1
                        yield text

    return generator()


def _normalize_name(raw: str) -> str:
    cleaned = raw
    for sep in (",", ";", "/", " oder ", " und "):
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0]
    if " (" in cleaned:
        cleaned = cleaned.split(" (", 1)[0]
    return cleaned.strip(" -*" + "\u00b7\u2022\n\t\r")


_CONNECTOR_WORDS = {"von", "van", "de", "del", "da", "la", "le"}


def _looks_like_name(candidate: str) -> bool:
    if not candidate:
        return False
    pieces = candidate.replace("-", " ").split()
    valid_parts = 0
    for piece in pieces:
        stripped = piece.strip(".'")
        if not stripped:
            continue
        if stripped.lower() in _CONNECTOR_WORDS:
            continue
        if not stripped[0].isalpha():
            return False
        if not stripped[0].isupper():
            return False
        valid_parts += 1
    return valid_parts > 0


def iter_pages() -> Iterator[dict]:
    for letter in ascii_lowercase:
        yield {
            "url": f"https://www.beliebte-vornamen.de/lexikon/{letter}-frau",
            "gender": "female",
        }
        yield {
            "url": f"https://www.beliebte-vornamen.de/lexikon/{letter}-mann",
            "gender": "male",
        }


def build_dataset(pages: Iterable[dict]) -> List[dict]:
    records: List[dict] = []
    seen_pairs = set()
    for page in pages:
        html = fetch_html(page["url"])
        names = extract_names(html)
        for name in names:
            key = (name, page["gender"])
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            records.append({"name": name, "gender": page["gender"], "source": page["url"]})
    return records


def save_json(records: List[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    dataset = build_dataset(iter_pages())
    save_json(dataset, OUTPUT_PATH)
    print(f"Saved {len(dataset)} names to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
