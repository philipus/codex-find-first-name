from __future__ import annotations

import unicodedata
from collections.abc import Callable

VOWELS = frozenset("aeiouy")
NUCLEUS_PATTERNS = (
    "aeu",  # normalized äu
    "ai",
    "ei",
    "oi",
    "ui",
    "au",
    "eu",
    "ae",
    "oe",
)
CONSONANT_CLUSTERS = ("sch", "ch", "ng", "ph")


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
    normalized_word, umlaut_u_flags = _normalize_german_word(word)
    syllables = _split_german_syllables(normalized_word, umlaut_u_flags)
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


def _normalize_german_word(word: str) -> tuple[str, list[bool]]:
    normalized_chars: list[str] = []
    umlaut_u_flags: list[bool] = []
    for char in word.lower():
        if char == "ä":
            normalized_chars.extend(("a", "e"))
            umlaut_u_flags.extend((False, False))
        elif char == "ö":
            normalized_chars.extend(("o", "e"))
            umlaut_u_flags.extend((False, False))
        elif char == "ü":
            normalized_chars.extend(("u", "e"))
            umlaut_u_flags.extend((True, False))
        elif char == "ß":
            normalized_chars.extend(("s", "s"))
            umlaut_u_flags.extend((False, False))
        else:
            normalized_chars.append(char)
            umlaut_u_flags.append(False)
    precomposed = "".join(normalized_chars)
    stripped, adjusted_flags = _strip_diacritics_preserving_flags(precomposed, umlaut_u_flags)
    return stripped, adjusted_flags


def _strip_diacritics_preserving_flags(text: str, flags: list[bool]) -> tuple[str, list[bool]]:
    """Remove combining marks while keeping umlaut metadata aligned."""
    stripped_chars: list[str] = []
    stripped_flags: list[bool] = []
    for char, flag in zip(text, flags):
        decomposed = unicodedata.normalize("NFKD", char)
        base_chars = [piece for piece in decomposed if not unicodedata.combining(piece)]
        if not base_chars:
            continue
        stripped_chars.extend(base_chars)
        if len(base_chars) == 1:
            stripped_flags.append(flag)
        else:
            stripped_flags.extend([flag] + [False] * (len(base_chars) - 1))
    return "".join(stripped_chars), stripped_flags


def _split_german_syllables(word: str, umlaut_u_flags: list[bool]) -> list[str]:
    if not word:
        return []

    working_word, working_flags = _prepare_working_german_word(word, umlaut_u_flags)
    vowel_nuclei = _find_vowel_nuclei(working_word, working_flags)
    if len(vowel_nuclei) <= 1:
        return [working_word] if working_word else []

    boundaries: list[int] = []
    for (_, current_end), (next_start, _) in zip(vowel_nuclei, vowel_nuclei[1:]):
        boundaries.append(_determine_syllable_boundary(working_word, current_end, next_start))
    return _slice_by_boundaries(working_word, boundaries)


def _prepare_working_german_word(word: str, umlaut_u_flags: list[bool]) -> tuple[str, list[bool]]:
    working_chars: list[str] = []
    working_flags: list[bool] = []
    for char, flag in zip(word, umlaut_u_flags):
        if char == "x":
            working_chars.extend(("k", "s"))
            working_flags.extend((False, False))
        else:
            working_chars.append(char)
            working_flags.append(flag)
    return "".join(working_chars), working_flags


def _find_vowel_nuclei(word: str, umlaut_u_flags: list[bool]) -> list[tuple[int, int]]:
    nuclei: list[tuple[int, int]] = []
    index = 0
    while index < len(word):
        if word[index] not in VOWELS:
            index += 1
            continue
        span = _match_vowel_nucleus(word, umlaut_u_flags, index)
        nuclei.append((index, index + span))
        index += span
    return nuclei


def _match_vowel_nucleus(word: str, umlaut_u_flags: list[bool], index: int) -> int:
    if word.startswith("ue", index) and umlaut_u_flags[index]:
        return 2
    for pattern in NUCLEUS_PATTERNS:
        if word.startswith(pattern, index):
            return len(pattern)
    if word.startswith("ia", index) and word.startswith("ne", index + 2):
        return 2
    return 1


def _determine_syllable_boundary(word: str, current_end: int, next_start: int) -> int:
    consonant_units = _extract_consonant_units(word, current_end, next_start)
    if not consonant_units:
        return next_start
    if len(consonant_units) == 1:
        return consonant_units[0][0]
    return consonant_units[-1][0]


def _extract_consonant_units(word: str, start: int, end: int) -> list[tuple[int, int]]:
    units: list[tuple[int, int]] = []
    index = start
    while index < end:
        matched = False
        for cluster in CONSONANT_CLUSTERS:
            if word.startswith(cluster, index):
                units.append((index, index + len(cluster)))
                index += len(cluster)
                matched = True
                break
        if matched:
            continue
        units.append((index, index + 1))
        index += 1
    return units


def _slice_by_boundaries(word: str, boundaries: list[int]) -> list[str]:
    syllables: list[str] = []
    start = 0
    for boundary in boundaries:
        syllables.append(word[start:boundary])
        start = boundary
    syllables.append(word[start:])
    return [syllable for syllable in syllables if syllable]
