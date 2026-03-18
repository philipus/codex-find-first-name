#!/usr/bin/env python3
"""Scrape beliebte-vornamen.de alphabetical name lists."""

from __future__ import annotations

import json
from pathlib import Path
import re
from string import ascii_lowercase
from typing import Iterable, Iterator, List

import requests
from bs4 import BeautifulSoup, Tag

OUTPUT_PATH = Path("data") / "all_names.json"
DECLARED_COUNT_PATTERN = re.compile(r"(\d+)\s+[A-Za-zÄÖÜäöüß]+namen", re.IGNORECASE)
_NAVIGATION_KEYWORDS = {"nav", "menu", "breadcrumb", "letter", "alphabet", "toc", "pager"}


def fetch_html(url: str) -> str:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def extract_declared_count(html_or_soup: str | BeautifulSoup) -> int | None:
    """Extract the declared number of names from the page title or heading."""
    if isinstance(html_or_soup, BeautifulSoup):
        soup = html_or_soup
    else:
        soup = BeautifulSoup(html_or_soup, "html.parser")

    texts: List[str] = []
    title = soup.find("title")
    if title:
        texts.append(title.get_text(" ", strip=True))
    for heading in soup.find_all(["h1", "h2"]):
        text = heading.get_text(" ", strip=True)
        if "namen" in text.lower():
            texts.append(text)
            break

    for text in texts:
        match = DECLARED_COUNT_PATTERN.search(text)
        if match:
            return int(match.group(1))

    fallback = DECLARED_COUNT_PATTERN.search(soup.get_text(" ", strip=True))
    if fallback:
        return int(fallback.group(1))
    return None


def extract_names(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if article is None:
        article = soup.find("main") or soup
    content = article.find(class_="entry-content") if isinstance(article, Tag) else None
    if content is None:
        content = article

    names: List[str] = []
    seen = set()
    declared_total = extract_declared_count(soup)

    def append_entries(entries: Iterable[str]) -> None:
        for text in entries:
            if not text:
                continue
            name = _normalize_name(text)
            if not name or not _looks_like_name(name) or name in seen:
                continue
            seen.add(name)
            names.append(name)

    candidate_lists = _find_name_lists(content)
    if candidate_lists:
        for candidate in candidate_lists:
            append_entries(_iter_list_entries(candidate))
    else:
        append_entries(_iter_link_names(content))

    if declared_total and len(names) < declared_total:
        append_entries(_iter_link_names(content))

    if not names:
        raise RuntimeError("Could not locate the primary name list on the page")
    return names


def _find_name_lists(content: Tag | None) -> List[Tag]:
    if content is None:
        return []

    candidates: List[tuple[int, Tag]] = []
    max_count = 0
    for node in content.find_all(["ul", "ol", "dl"]):
        if _looks_like_navigation_list(node):
            continue
        entry_count = _list_entry_count(node)
        if entry_count == 0:
            continue
        candidates.append((entry_count, node))
        if entry_count > max_count:
            max_count = entry_count

    if not candidates:
        return []

    threshold = max(max_count // 3, 20)
    selected = [node for count, node in candidates if count >= threshold]
    if selected:
        return selected
    # Fallback to the single largest list if no list crossed the threshold.
    largest = max(candidates, key=lambda item: item[0])[1]
    return [largest]


def _list_entry_count(tag: Tag) -> int:
    if tag.name == "dl":
        entries = tag.find_all("dt", recursive=False)
        if not entries:
            entries = tag.find_all("dt")
    else:
        entries = tag.find_all("li", recursive=False)
        if not entries:
            entries = tag.find_all("li")
    return len(entries)


def _iter_list_entries(tag: Tag) -> Iterable[str]:
    if tag.name == "dl":
        entries = tag.find_all("dt", recursive=False)
        if not entries:
            entries = tag.find_all("dt")
    else:
        entries = tag.find_all("li", recursive=False)
        if not entries:
            entries = tag.find_all("li")
    for node in entries:
        if isinstance(node, Tag):
            yield node.get_text(" ", strip=True)


def _looks_like_navigation_list(tag: Tag) -> bool:
    marker = " ".join(tag.get("class", [])) + " " + (tag.get("id") or "") + " " + (tag.get("role") or "")
    marker = marker.lower()
    if any(keyword in marker for keyword in _NAVIGATION_KEYWORDS):
        return True
    ancestor = tag.parent
    while isinstance(ancestor, Tag):
        if ancestor.name == "nav":
            return True
        ancestor = ancestor.parent
    return False


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
