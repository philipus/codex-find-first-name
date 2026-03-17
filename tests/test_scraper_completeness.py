from __future__ import annotations

from pathlib import Path

import pytest

from scrape_beliebte_names import extract_names, extract_declared_count


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    path = FIXTURE_DIR / name
    return path.read_text(encoding="utf-8")


def test_declared_count_a_frau() -> None:
    html = load_fixture("a_frau.html")
    count = extract_declared_count(html)
    assert count == 308


def test_declared_count_a_mann() -> None:
    html = load_fixture("a_mann.html")
    count = extract_declared_count(html)
    assert count == 287


@pytest.mark.parametrize(
    "fixture_name",
    ["a_frau.html", "a_mann.html"],
)
def test_name_count_matches_declared_count(fixture_name: str) -> None:
    html = load_fixture(fixture_name)
    declared = extract_declared_count(html)
    assert declared is not None
    names = extract_names(html)
    assert len(names) == declared
