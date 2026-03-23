from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.review_phonetics_sample import (
    ReviewStats,
    build_summary,
    create_review_record,
    format_summary,
    load_names_from_json,
    parse_corrected_syllables,
    sample_names,
)


def test_load_names_from_json_supports_strings_and_objects(tmp_path: Path) -> None:
    data_path = tmp_path / "names.json"
    data_path.write_text(json.dumps(["Anna", {"name": "Berta"}]), encoding="utf-8")

    result = load_names_from_json(data_path)

    assert result == ["Anna", "Berta"]


def test_sample_names_is_deterministic(tmp_path: Path) -> None:
    names = ["Anna", "Berta", "Clara", "Dora", "Eva"]

    first = sample_names(names, 3, seed=42)
    second = sample_names(names, 3, seed=42)

    assert first == second
    assert len(first) == 3
    assert set(first).issubset(set(names))


def test_sample_names_returns_all_when_count_exceeds_pool() -> None:
    names = ["Anna", "Berta"]

    sampled = sample_names(names, 10, seed=1)

    assert set(sampled) == set(names)
    assert len(sampled) == len(names)


def test_parse_corrected_syllables_trims_input() -> None:
    assert parse_corrected_syllables("li, an ,an ") == ["li", "an", "an"]


def test_parse_corrected_syllables_requires_value() -> None:
    with pytest.raises(ValueError):
        parse_corrected_syllables("   ,  ")


def test_create_review_record_includes_expected_fields() -> None:
    analysis = {
        "normalized_word": "maximilian",
        "syllables": ["mak", "si"],
        "syllable_count": 2,
    }

    record = create_review_record("Maximilian", "de", analysis, 0, ["mak", "si"])

    assert record["name"] == "Maximilian"
    assert record["predicted_syllables"] == ["mak", "si"]
    assert record["corrected_syllables"] == ["mak", "si"]
    assert record["label"] == 0


def test_build_and_format_summary_reports_counts() -> None:
    records = [
        {"name": "Anna", "label": 1, "predicted_syllables": ["an"], "corrected_syllables": None},
        {
            "name": "Berta",
            "label": 0,
            "predicted_syllables": ["ber"],
            "corrected_syllables": ["ber", "ta"],
        },
    ]

    stats = build_summary(sampled=5, reviewed_records=records, quit_early=True)
    summary_text = format_summary(stats)

    assert stats.good == 1
    assert stats.bad == 1
    assert "Sampled: 5" in summary_text
    assert "Quit early: yes" in summary_text
    assert "Berta" in summary_text
    assert "['ber', 'ta']" in summary_text
