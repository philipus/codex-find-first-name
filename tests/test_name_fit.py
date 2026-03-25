from __future__ import annotations

from unittest.mock import patch

import pytest

from name_finder.name_fit import extract_name_fit_features, score_name_fit


def test_score_name_fit_returns_expected_structure_and_fixed_values() -> None:
    result = score_name_fit("Lian", "Floegel")

    assert result["first_name"] == "Lian"
    assert result["surname"] == "Floegel"
    assert result["language"] == "de"

    features = result["feature_values"]
    assert features["first_name_syllables"] == ["li", "an"]
    assert features["surname_syllables"] == ["floe", "gel"]
    assert features["first_name_syllable_count"] == 2
    assert features["surname_syllable_count"] == 2
    assert features["absolute_syllable_count_difference"] == 0
    assert features["first_syllable_match"] is False
    assert features["last_syllable_match"] is False
    assert features["levenshtein_distance"] == 2
    assert features["normalized_similarity_score"] == pytest.approx(0.0)

    components = result["component_scores"]
    assert components["syllable_balance"]["contribution"] == pytest.approx(0.25)
    assert components["first_syllable_alignment"]["contribution"] == pytest.approx(0.0)
    assert components["last_syllable_alignment"]["contribution"] == pytest.approx(0.0)
    assert components["sequence_similarity"]["contribution"] == pytest.approx(0.0)
    assert result["overall_score"] == pytest.approx(0.25)
    assert result["overall_score_percent"] == pytest.approx(25.0)


def test_score_name_fit_overall_score_is_sum_of_component_contributions() -> None:
    result = score_name_fit("Floegel", "Floegel")

    contributions = [
        component["contribution"] for component in result["component_scores"].values()
    ]
    assert contributions == pytest.approx([0.25, 0.15, 0.2, 0.4])
    assert sum(contributions) == pytest.approx(result["overall_score"])
    assert result["overall_score"] == pytest.approx(1.0)
    assert result["overall_score_percent"] == pytest.approx(100.0)


def test_extract_name_fit_features_reuses_compare_syllables() -> None:
    compare_result = {
        "syllable_count_diff": 1,
        "first_syllable_match": True,
        "last_syllable_match": False,
        "levenshtein_distance": 2,
        "normalized_similarity_score": 0.5,
    }

    with (
        patch("name_finder.name_fit.compare_syllables", return_value=compare_result) as mocked_compare,
        patch(
            "name_finder.name_fit.analyze_word",
            side_effect=[
                {"syllables": ["ma", "ri"], "syllable_count": 2},
                {"syllables": ["mei", "er"], "syllable_count": 2},
            ],
        ) as mocked_analyze,
    ):
        features = extract_name_fit_features("Marie", "Meier")

    mocked_compare.assert_called_once_with("Marie", "Meier", language="de")
    assert mocked_analyze.call_count == 2
    assert features == {
        "first_name_syllables": ["ma", "ri"],
        "surname_syllables": ["mei", "er"],
        "first_name_syllable_count": 2,
        "surname_syllable_count": 2,
        "absolute_syllable_count_difference": 1,
        "first_syllable_match": True,
        "last_syllable_match": False,
        "levenshtein_distance": 2,
        "normalized_similarity_score": 0.5,
    }
