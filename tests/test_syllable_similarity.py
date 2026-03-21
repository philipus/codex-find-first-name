from __future__ import annotations

import pytest

from name_finder.syllable_similarity import compare_syllables


@pytest.mark.parametrize(
    ("name1", "name2", "expected"),
    [
        (
            "Lian",
            "Floegel",
            {
                "syllables1": ["lian"],
                "syllables2": ["floe", "gel"],
                "syllable_count_diff": 1,
                "first_syllable_match": False,
                "last_syllable_match": False,
                "levenshtein_distance": 2,
                "normalized_similarity_score": 0.0,
            },
        ),
        (
            "Maximilian",
            "Floegel",
            {
                "syllables1": ["ma", "xi", "mi", "lian"],
                "syllables2": ["floe", "gel"],
                "syllable_count_diff": 2,
                "first_syllable_match": False,
                "last_syllable_match": False,
                "levenshtein_distance": 4,
                "normalized_similarity_score": 0.0,
            },
        ),
    ],
)
def test_compare_syllables_returns_expected_metrics(
    name1: str,
    name2: str,
    expected: dict,
) -> None:
    result = compare_syllables(name1, name2)

    assert result["name1"] == name1
    assert result["name2"] == name2
    assert result["syllables1"] == expected["syllables1"]
    assert result["syllables2"] == expected["syllables2"]
    assert result["syllable_count_diff"] == expected["syllable_count_diff"]
    assert result["first_syllable_match"] is expected["first_syllable_match"]
    assert result["last_syllable_match"] is expected["last_syllable_match"]
    assert result["levenshtein_distance"] == expected["levenshtein_distance"]
    assert result["normalized_similarity_score"] == pytest.approx(
        expected["normalized_similarity_score"]
    )


def test_compare_syllables_identical_names_have_zero_distance_and_full_score() -> None:
    result = compare_syllables("Floegel", "Floegel")

    assert result["syllables1"] == ["floe", "gel"]
    assert result["syllables2"] == ["floe", "gel"]
    assert result["syllable_count_diff"] == 0
    assert result["first_syllable_match"] is True
    assert result["last_syllable_match"] is True
    assert result["levenshtein_distance"] == 0
    assert result["normalized_similarity_score"] == pytest.approx(1.0)


def test_compare_syllables_keeps_score_within_bounds() -> None:
    results = [
        compare_syllables("Lian", "Floegel"),
        compare_syllables("Maximilian", "Floegel"),
        compare_syllables("Floegel", "Floegel"),
    ]

    for result in results:
        assert 0.0 <= result["normalized_similarity_score"] <= 1.0
