from __future__ import annotations

import pytest

from name_finder.phonetics import UnsupportedLanguageError, analyze_word


REQUIRED_KEYS = {
    "original_word",
    "normalized_word",
    "language",
    "syllables",
    "syllable_count",
}


@pytest.mark.parametrize(
    ("word", "expected_normalized", "expected_syllables"),
    [
        ("Floegel", "floegel", ["floe", "gel"]),
        ("Flögel", "floegel", ["floe", "gel"]),
        ("Garten", "garten", ["gar", "ten"]),
        ("Lian", "lian", ["li", "an"]),
        ("Liane", "liane", ["lia", "ne"]),
        ("Emanuel", "emanuel", ["e", "ma", "nu", "el"]),
        ("Maximilian", "maximilian", ["mak", "si", "mi", "li", "an"]),
    ],
)
def test_analyze_word_returns_expected_german_profile(
    word: str,
    expected_normalized: str,
    expected_syllables: list[str],
) -> None:
    result = analyze_word(word, language="de")

    assert REQUIRED_KEYS <= result.keys()
    assert result["original_word"] == word
    assert result["normalized_word"] == expected_normalized
    assert result["language"] == "de"
    assert result["syllables"] == expected_syllables
    assert result["syllable_count"] == len(result["syllables"]) == len(expected_syllables)


def test_analyze_word_normalizes_umlauts_to_ascii_sequences() -> None:
    result = analyze_word("Müller", language="de")

    assert result["normalized_word"] == "mueller"
    assert result["syllables"] == ["muel", "ler"]
    assert result["syllable_count"] == 2


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("Flögel", "floegel"),
        ("Floegel", "floegel"),
        ("Václaw", "vaclaw"),
        ("Émile", "emile"),
        ("Müller", "mueller"),
        ("straße", "strasse"),
    ],
)
def test_normalization_handles_umlauts_and_general_diacritics(word: str, expected: str) -> None:
    result = analyze_word(word, language="de")

    assert result["normalized_word"] == expected


def test_analyze_word_rejects_unsupported_languages_explicitly() -> None:
    with pytest.raises(UnsupportedLanguageError, match="Unsupported language: 'en'"):
        analyze_word("Floegel", language="en")
