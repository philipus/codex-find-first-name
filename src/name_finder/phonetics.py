from __future__ import annotations

from collections.abc import Callable

GERMAN_UMLAUT_MAP = str.maketrans({
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
})
VOWELS = frozenset("aeiouy")


class UnsupportedLanguageError(ValueError):
    """Raised when no phonetic analyzer is registered for a language."""


def analyze_word(word: str, language: str) -> dict:
    """Return a deterministic phonetic profile for a word and language."""
    analyzer = _get_language_analyzer(language)
    return analyzer(word)


def _get_language_analyzer(language: str) -> Callable[[str], dict]:
    analyzer = _LANGUAGE_ANALYZERS.get(language)
    if analyzer is None:
        supported = ", ".join(sorted(_LANGUAGE_ANALYZERS))
        raise UnsupportedLanguageError(
            f"Unsupported language: {language!r}. Supported languages: {supported}"
        )
    return analyzer


def _analyze_german_word(word: str) -> dict:
    normalized_word = _normalize_german_word(word)
    syllables = _split_german_syllables(normalized_word)
    return {
        "original_word": word,
        "normalized_word": normalized_word,
        "language": "de",
        "syllables": syllables,
        "syllable_count": len(syllables),
    }


_LANGUAGE_ANALYZERS: dict[str, Callable[[str], dict]] = {
    "de": _analyze_german_word,
}


def _normalize_german_word(word: str) -> str:
    return word.lower().translate(GERMAN_UMLAUT_MAP)


def _split_german_syllables(word: str) -> list[str]:
    if not word:
        return []

    vowel_groups = _find_vowel_groups(word)
    if len(vowel_groups) <= 1:
        return [word]

    boundaries: list[int] = []
    for (_, current_end), (next_start, _) in zip(vowel_groups, vowel_groups[1:]):
        boundaries.append(_syllable_boundary(current_end, next_start))
    return _slice_by_boundaries(word, boundaries)


def _find_vowel_groups(word: str) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    index = 0
    while index < len(word):
        if word[index] not in VOWELS:
            index += 1
            continue
        start = index
        while index < len(word) and word[index] in VOWELS:
            index += 1
        groups.append((start, index))
    return groups


def _syllable_boundary(current_end: int, next_start: int) -> int:
    consonant_count = next_start - current_end
    if consonant_count <= 1:
        return current_end
    return next_start - 1


def _slice_by_boundaries(word: str, boundaries: list[int]) -> list[str]:
    syllables: list[str] = []
    start = 0
    for boundary in boundaries:
        syllables.append(word[start:boundary])
        start = boundary
    syllables.append(word[start:])
    return [syllable for syllable in syllables if syllable]
